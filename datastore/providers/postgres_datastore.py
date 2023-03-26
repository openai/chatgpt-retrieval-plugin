import os
from typing import Dict, List, Optional
from datetime import datetime
from psycopg2 import connect
from psycopg2.extras import Json, DictCursor

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

DATABASE_URL = os.environ.get("DATABASE_URL")


# class that implements the DataStore interface for Supabase Datastore provider
class PostgresDataStore(DataStore):
    def __init__(self):
        self.conn = connect(DATABASE_URL, sslmode='require')
        cur = self.conn.cursor()
        cur.execute(
            """
              CREATE EXTENSION IF NOT EXISTS vector;
              CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

            """
        )

        cur.execute(
            """
              CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::TEXT,
                source TEXT,
                source_id TEXT,
                content TEXT,
                document_id TEXT,
                author TEXT,
                url TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                embedding VECTOR(1536)
            );
            """
        )

        self.conn.commit()

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict of document_ids to list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        for document_id, document_chunks in chunks.items():
            for chunk in document_chunks:
                created_at = (
                  datetime.fromtimestamp(to_unix_timestamp(chunk.metadata.created_at))
                  if chunk.metadata.created_at
                  else None
)
                data = (
                    chunk.id,
                    chunk.text,
                    chunk.embedding,
                    document_id,
                    chunk.metadata.source,
                    chunk.metadata.source_id,
                    chunk.metadata.url,
                    chunk.metadata.author,
                    created_at
                )

                cur = self.conn.cursor()
                # Construct the SQL query and data
                query = """
                    INSERT INTO documents (id, content, embedding, document_id, source, source_id, url, author, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """

                # Execute the query
                cur.execute(query, data)

                # Commit the transaction
                self.conn.commit()

        return list(chunks.keys())

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        query_results: List[QueryResult] = []
        
        def generate_query(query):
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
                  (embedding <=> '{embedding}') * -1 AS similarity
              FROM
                  documents
          """
          q += generate_where_clause(query.filter)
          q += f"ORDER BY similarity LIMIT {query.top_k};"
          return q

        def generate_where_clause(query_filter):
            if not query_filter:
                return ""

            where_conditions = []
            if query_filter.document_id:
                where_conditions.append(f"document_id='{query_filter.document_id}'")
            if query_filter.source_id:
                where_conditions.append(f"source_id='{query_filter.source_id}'")
            if query_filter.source:
                where_conditions.append(f"source LIKE '{query_filter.source}'")
            if query_filter.author:
                where_conditions.append(f"author LIKE '{query_filter.author}'")
            if query_filter.start_date:
                where_conditions.append(f"created_at >= '{query_filter.start_date}'")
            if query_filter.end_date:
                where_conditions.append(f"created_at <= '{query_filter.end_date}'")

            return "WHERE " + " AND ".join(where_conditions) + " "

        def fetch_data(cur, q):
            cur.execute(q)
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
        
        for query in queries:
            try:
                cur = self.conn.cursor(cursor_factory=DictCursor)
                for query in queries:
                    q = generate_query(query)
                    data = fetch_data(cur, q)
                    results = create_results(data)
                    query_results.append(QueryResult(query=query.query, results=results))
            except Exception as e:
                print("error:", e)
                query_results.append(QueryResult(query=query.query, results=[]))
        return query_results

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        """
        try:
            cur = self.conn.cursor()
            
            if delete_all:
                query = "DELETE FROM documents WHERE document_id LIKE '%';"
            elif ids:
                query = f"DELETE FROM documents WHERE document_id IN ('{', '.join(map(str, ids))}');"
            elif filter:
                where_conditions = []
                if filter.document_id:
                    where_conditions.append(f"document_id <= '{filter.document_id}'")
                if filter.source:
                    where_conditions.append(f"source = '{filter.source}'")
                if filter.source_id:
                    where_conditions.append(f"source_id = '{filter.source_id}'")
                if filter.author:
                    where_conditions.append(f"author = '{filter.author}'")
                if filter.start_date:
                    start_date = datetime.fromtimestamp(to_unix_timestamp(filter.start_date))
                    where_conditions.append(f"created_at >= '{start_date}'")
                if filter.end_date:
                    end_date = datetime.fromtimestamp(to_unix_timestamp(filter.end_date))
                    where_conditions.append(f"created_at <= '{end_date}'")
                query = f"DELETE FROM documents WHERE {' AND '.join(where_conditions)};"
            else:
                return True

            cur.execute(query)
            self.conn.commit()
            return True
        
        except Exception as e:
          print(f"Error: {e}")
          return False