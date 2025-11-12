import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from loguru import logger

from psycopg2cffi import compat

compat.register()
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from services.date import to_unix_timestamp
from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    DocumentChunkWithScore,
)

PG_CONFIG = {
    "collection": os.environ.get("PG_COLLECTION", "document_chunks"),
    "database": os.environ.get("PG_DATABASE", "postgres"),
    "user": os.environ.get("PG_USER", "user"),
    "password": os.environ.get("PG_PASSWORD", "password"),
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": int(os.environ.get("PG_PORT", "5432")),
}
OUTPUT_DIM = int(os.environ.get("EMBEDDING_DIMENSION", 256))


class AnalyticDBDataStore(DataStore):
    def __init__(self, config: Dict[str, str] = PG_CONFIG):
        self.collection_name = config["collection"]
        self.user = config["user"]
        self.password = config["password"]
        self.database = config["database"]
        self.host = config["host"]
        self.port = config["port"]

        self.connection_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=100,
            dbname=self.database,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
        )

        self._initialize_db()

    def _initialize_db(self):
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                self._create_table(cur)
                self._create_embedding_index(cur)
                conn.commit()
        finally:
            self.connection_pool.putconn(conn)

    def _create_table(self, cur: psycopg2.extensions.cursor):
        cur.execute(
            f"""
              CREATE TABLE IF NOT EXISTS {self.collection_name} (
                id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::TEXT,
                source TEXT,
                source_id TEXT,
                content TEXT,
                document_id TEXT,
                author TEXT,
                url TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                embedding real[]
            );
            """
        )

    def _create_embedding_index(self, cur: psycopg2.extensions.cursor):
        cur.execute(
            f"""
            SELECT * FROM pg_indexes WHERE tablename='{self.collection_name}';
            """
        )
        index_exists = any(
            index[2] == f"{self.collection_name}_embedding_idx"
            for index in cur.fetchall()
        )
        if not index_exists:
            cur.execute(
                f"""
                CREATE INDEX {self.collection_name}_embedding_idx
                ON {self.collection_name}
                USING ann(embedding)
                WITH (
                    distancemeasure=L2,
                    dim=OUTPUT_DIM,
                    pq_segments=64,
                    hnsw_m=100,
                    pq_centers=2048
                );
                """
            )

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict of document_ids to list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(None, self._upsert_chunk, chunk)
            for document_chunks in chunks.values()
            for chunk in document_chunks
        ]
        await asyncio.gather(*tasks)

        return list(chunks.keys())

    def _upsert_chunk(self, chunk: DocumentChunk):
        created_at = (
            datetime.fromtimestamp(to_unix_timestamp(chunk.metadata.created_at))
            if chunk.metadata.created_at
            else None
        )
        data = (
            chunk.id,
            chunk.text,
            chunk.embedding,
            chunk.metadata.document_id,
            chunk.metadata.source,
            chunk.metadata.source_id,
            chunk.metadata.url,
            chunk.metadata.author,
            created_at,
        )

        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Construct the SQL query and data
                query = f"""
                        INSERT INTO {self.collection_name} (id, content, embedding, document_id, source, source_id, url, author, created_at)
                        VALUES (%s::text, %s::text, %s::real[], %s::text, %s::text, %s::text, %s::text, %s::text, %s::timestamp with time zone)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            document_id = EXCLUDED.document_id,
                            source = EXCLUDED.source,
                            source_id = EXCLUDED.source_id,
                            url = EXCLUDED.url,
                            author = EXCLUDED.author,
                            created_at = EXCLUDED.created_at;
                """

                # Execute the query
                cur.execute(query, data)

                # Commit the transaction
                conn.commit()
        finally:
            self.connection_pool.putconn(conn)

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        query_results: List[QueryResult] = []

        def generate_query(query: QueryWithEmbedding) -> Tuple[str, List[Any]]:
            embedding = "[" + ", ".join(str(x) for x in query.embedding) + "]"
            q = f"""
                SELECT
                    id,
                    content,
                    source,
                    source_id,
                    document_id,
                    url,
                    created_at,
                    author,
                    embedding,
                    l2_distance(embedding,array{embedding}::real[]) AS similarity
                FROM
                    {self.collection_name}
            """
            where_clause, params = generate_where_clause(query.filter)
            q += where_clause
            q += f"ORDER BY embedding <-> array{embedding}::real[] LIMIT {query.top_k};"
            return q, params

        def generate_where_clause(
            query_filter: Optional[DocumentMetadataFilter],
        ) -> Tuple[str, List[Any]]:
            if query_filter is None:
                return "", []

            conditions = [
                ("document_id=%s", query_filter.document_id),
                ("source_id=%s", query_filter.source_id),
                ("source LIKE %s", query_filter.source),
                ("author LIKE %s", query_filter.author),
                ("created_at >= %s", query_filter.start_date),
                ("created_at <= %s", query_filter.end_date),
            ]

            where_clause = "WHERE " + " AND ".join(
                [cond[0] for cond in conditions if cond[1] is not None]
            )

            values = [cond[1] for cond in conditions if cond[1] is not None]

            return where_clause, values

        def fetch_data(cur, q: str, params: List[Any]):
            cur.execute(q, params)
            return cur.fetchall()

        def create_results(data):
            results = []
            for row in data:
                document_chunk = DocumentChunkWithScore(
                    id=row["id"],
                    text=row["content"],
                    score=float(row["similarity"]),
                    metadata=DocumentChunkMetadata(
                        source=row["source"],
                        source_id=row["source_id"],
                        document_id=row["document_id"],
                        url=row["url"],
                        created_at=str(row["created_at"]),
                        author=row["author"],
                    ),
                )
                results.append(document_chunk)
            return results

        conn = self.connection_pool.getconn()
        try:
            for query in queries:
                try:
                    cur = conn.cursor(cursor_factory=DictCursor)
                    for query in queries:
                        q, params = generate_query(query)
                        data = fetch_data(cur, q, params)
                        results = create_results(data)
                        query_results.append(
                            QueryResult(query=query.query, results=results)
                        )
                except Exception as e:
                    logger.error(e)
                    query_results.append(QueryResult(query=query.query, results=[]))
            return query_results
        finally:
            self.connection_pool.putconn(conn)

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        async def execute_delete(query: str, params: Optional[List] = None) -> bool:
            conn = self.connection_pool.getconn()
            try:
                with conn.cursor() as cur:
                    if params:
                        cur.execute(query, params)
                    else:
                        cur.execute(query)
                    self.conn.commit()
                return True
            except Exception as e:
                logger.error(e)
                return False
            finally:
                self.connection_pool.putconn(conn)

        if delete_all:
            query = f"DELETE FROM {self.collection_name} WHERE document_id LIKE %s;"
            return await execute_delete(query, ["%"])
        elif ids:
            query = f"DELETE FROM {self.collection_name} WHERE document_id IN ({','.join(['%s'] * len(ids))});"
            return await execute_delete(query, ids)
        elif filter is not None:
            query, params = self._generate_delete_query(filter)
            return await execute_delete(query, params)
        else:
            return True

    def _generate_delete_query(
        self, filter: DocumentMetadataFilter
    ) -> Tuple[str, List]:
        conditions = [
            (filter.document_id, "document_id = %s"),
            (filter.source, "source = %s"),
            (filter.source_id, "source_id = %s"),
            (filter.author, "author = %s"),
            (filter.start_date, "created_at >= %s"),
            (filter.end_date, "created_at <= %s"),
        ]

        where_conditions = [f for value, f in conditions if value]
        where_values = [value for value, _ in conditions if value]

        query = f"DELETE FROM {self.collection_name} WHERE {' AND '.join(where_conditions)};"
        return query, where_values
