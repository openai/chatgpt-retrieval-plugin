import os
from typing import Any, Tuple, Dict, List, Optional
from datetime import datetime
from services.date import to_unix_timestamp
from loguru import logger

from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)

import psycopg2

OUTPUT_DIM = 1536

PGHOST = os.environ.get("PGHOST", "localhost")
PGPORT = int(os.environ.get("PGPORT", 80))
PGUSER = os.environ.get("PGUSER", "BASIC$user")
PGPASSWORD = os.environ.get("PGPASSWORD", "password")
PGDB = os.environ.get("PGDATABASE", "postgres")
PGTABLENAME = os.environ.get("PGTABLENAME", "document_chunks")


class HoloClient():
    def __init__(self, host: str, port: int, user: str, password: str, db: str) -> None:
        self.conn = psycopg2.connect(
            host=host, port=port, database=db, user=user, password=password)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

    def __del__(self) -> None:
        # close the connection when the client is destroyed
        self.conn.close()

    def execute(self, sql: str, vars: Tuple = None):
        self.cursor.execute(sql, vars)

    def commit(self) -> None:
        self.conn.commit()

    def query(self, sql: str, vars: Tuple = None) -> List[Tuple]:
        self.cursor.execute(sql, vars)
        self.conn.commit()
        return self.cursor.fetchall()


class HologresDataStore(DataStore):
    def __init__(self) -> None:
        super().__init__()
        self.table_name = PGTABLENAME
        self.client = HoloClient(PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDB)
        self.ndims = OUTPUT_DIM
        try:
            self._create_table()
        except Exception as e:
            logger.error(e)
            raise Exception(f'Init hologres datastore failed: {e}')

    def _create_table(self) -> None:
        """
        Create the table to store document chunks.
        """
        self.client.execute("create extension if not exists proxima")
        self.client.commit()

        sql = f"""create table if not exists {self.table_name} (
            id text primary key,
            source text,
            source_id text,
            content text,
            document_id text,
            author text,
            url text,
            created_at timestamptz default now(),
            embedding float4[] check(array_ndims(embedding) = 1 and array_length(embedding, 1) = {self.ndims})
            );"""
        self.client.execute(sql)
        sql = f"call set_table_property('{self.table_name}'" + """, 'proxima_vectors', 
            '{"embedding":{"algorithm":"Graph",
            "distance_method":"SquaredEuclidean",
            "build_params":{"min_flush_proxima_row_count" : 1,
            "min_compaction_proxima_row_count" : 1, 
            "max_total_size_to_merge_mb" : 2000}}}');"""
        self.client.execute(sql)
        self.client.commit()

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        for document_chunks in chunks.values():
            for chunk in document_chunks:
                print(f"upsert: {chunk}")
                self._upsert_chunk(chunk)

        return list(chunks.keys())

    def _upsert_chunk(self, chunk: DocumentChunk) -> None:
        """Takes in a document chunk and upsert it in the datastore."""
        created_at = (
            datetime.fromtimestamp(
                to_unix_timestamp(chunk.metadata.created_at))
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

        try:
            # Construct the SQL query and data
            query = f"""
                    INSERT INTO "{self.table_name}" (id, content, embedding, document_id, source, source_id, url, author, created_at)
                    VALUES (%s::text, %s::text, %s::float4[], %s::text, %s::text, %s::text, %s::text, %s::text, %s::timestamptz)
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
            self.client.execute(query, data)

            # Commit the transaction
            self.client.commit()
        except Exception as e:
            logger.error(f'Upsert failed: {e}')

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
                    pm_approx_squared_euclidean_distance(embedding,array{embedding}::real[]) AS distance 
                FROM
                    {self.table_name}
            """
            where_clause, params = generate_where_clause(query.filter)
            q += where_clause
            q += f"ORDER BY distance LIMIT {query.top_k};"
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

        def create_results(data):
            results = []
            for row in data:
                document_chunk = DocumentChunkWithScore(
                    id=row[0],
                    text=row[1],
                    metadata=DocumentChunkMetadata(
                        source=row[2],
                        source_id=row[3],
                        document_id=row[4],
                        url=row[5],
                        created_at=str(row[6]),
                        author=row[7],
                    ),
                    score=float(row[9]),
                )
                results.append(document_chunk)
            return results

        for query in queries:
            try:
                q, params = generate_query(query)
                data = self.client.query(q, params)
                results = create_results(data)
                query_results.append(
                    QueryResult(query=query.query, results=results)
                )
            except Exception as e:
                logger.error(e)
                query_results.append(QueryResult(
                    query=query.query, results=[]))
        return query_results

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Multiple parameters can be used at once.
        Returns whether the operation was successful.
        """
        def execute_delete(query: str, params: Optional[List] = None) -> bool:
            try:
                self.client.execute(query, params)
                self.client.commit()
                return True
            except Exception as e:
                logger.error(e)
                return False

        if delete_all:
            query = f"truncate table {self.table_name};"
            return execute_delete(query)
        elif ids:
            query = f"DELETE FROM {self.table_name} WHERE document_id IN ({','.join(['%s'] * len(ids))});"
            return execute_delete(query, ids)
        elif filter is not None:
            query, params = self._generate_delete_query(filter)
            return execute_delete(query, params)
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

        query = f"DELETE FROM {self.table_name} WHERE {' AND '.join(where_conditions)};"
        return query, where_values
