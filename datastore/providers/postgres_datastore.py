import os
from typing import Dict, List, Optional
from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)
import json
import psycopg
from psycopg import sql

from services.date import to_unix_timestamp

# Read environment variables for Postgres

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", 5433))
POSTGRES_USERNAME = os.environ.get("POSTGRES_USERNAME", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "pgml_development")
POSTGRES_TABLENAME = os.environ.get("POSTGRES_TABLENAME", "chatgpt_datastore")
POSTGRES_SYNCHRONOUS_COMMIT = os.environ.get(
    "POSTGRES_SYNCHRONOUS_COMMIT", "off"
).lower()

assert POSTGRES_SYNCHRONOUS_COMMIT in ["on", "off"]
# OpenAI Ada Embeddings Dimension
VECTOR_DIMENSION = 1536


class PostgresDataStore(DataStore):
    def __init__(self) -> None:
        self.conn_params = {
            "dbname": POSTGRES_DATABASE,
            "user": POSTGRES_USERNAME,
            "password": POSTGRES_PASSWORD,
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
        }
        conn = psycopg.connect(**self.conn_params)
        # Insert the vector and text into the database
        create_table = (
            "CREATE TABLE IF NOT EXISTS %s (doc_id TEXT, chunk_id TEXT, text TEXT, embedding vector(%s), metadata JSONB)"
            % (POSTGRES_TABLENAME, str(VECTOR_DIMENSION))
        )
        cur = conn.cursor()
        cur.execute(create_table)
        # Commit the transaction
        conn.commit()
        # Close the cursor and the connection
        cur.close()
        conn.close()

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict from document id to list of document chunks and inserts them into the index.
        Return a list of document ids.
        """
        # Create a connection
        conn = psycopg.connect(**self.conn_params)
        cur = conn.cursor()

        # Initialize a list of ids to return
        doc_ids: List[str] = []

        # Set synchronous commit
        cur.execute("SET synchronous_commit = %s" % POSTGRES_SYNCHRONOUS_COMMIT)

        with cur.copy(
            "COPY %s (doc_id, chunk_id, text, embedding, metadata) FROM STDIN"
            % POSTGRES_TABLENAME
        ) as copy:
            for doc_id, chunk_list in chunks.items():
                doc_ids.append(doc_id)
                for chunk in chunk_list:
                    text = sql.Literal(chunk.text).as_string(conn)
                    embedding = "[" + ",".join([str(v) for v in chunk.embedding]) + "]"

                    metadata = chunk.metadata.dict()
                    if "created_at" in list(metadata.keys()):
                        if metadata["created_at"]:
                            metadata["created_at"] = to_unix_timestamp(
                                metadata["created_at"]
                            )
                    metadata = json.dumps(metadata)

                    row = (doc_id, chunk.id, text, embedding, metadata)
                    copy.write_row(row)

        index_statement = (
            "CREATE INDEX ON %s USING ivfflat (embedding vector_cosine_ops)"
            % POSTGRES_TABLENAME
        )
        cur.execute(index_statement)

        conn.commit()
        cur.close()
        conn.close()

        return doc_ids

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and
        returns a list of query results with matching document chunks and scores.
        """
        # Prepare query responses and results object
        results: List[QueryResult] = []

        # Create a connection
        conn = psycopg.connect(**self.conn_params)
        cur = conn.cursor()

        for query in queries:
            query_results: List[DocumentChunkWithScore] = []
            embedding = ",".join(str(v) for v in query.embedding)
            query_statement = (
                "SELECT doc_id, text, metadata, 1 - (%s.embedding <=> ARRAY[%s]::vector) AS score FROM %s ORDER BY score DESC LIMIT %d;"
                % (
                    POSTGRES_TABLENAME,
                    embedding,
                    POSTGRES_TABLENAME,
                    query.top_k,
                )
            )
            cur.execute(query_statement)
            sql_query_results = cur.fetchall()

            query_results: List[DocumentChunkWithScore] = []
            for result in sql_query_results:
                doc_id = result[0]
                text = result[1]
                metadata = result[2]
                score = result[3]
                query_result = DocumentChunkWithScore(
                    id=doc_id, score=score, text=text, metadata=(metadata)
                )
                query_results.append(query_result)

        results.append(QueryResult(query=query.query, results=query_results))

        cur.close()
        conn.close()

        return results

    async def delete(
        self,
        ids: List[str] | None = None,
        filter: DocumentMetadataFilter | None = None,
        delete_all: bool | None = None,
    ) -> bool:
        # Create a connection
        conn = psycopg.connect(**self.conn_params)
        cur = conn.cursor()

        if delete_all:
            delete_statement = "DELETE FROM {}".format(
                sql.Identifier(POSTGRES_TABLENAME)
            )
            try:
                cur.execute(delete_statement)
            except Exception as e:
                print(e)

        if filter:
            counter = 0
            delete_statement = "DELETE FROM %s" % POSTGRES_TABLENAME

            for key, value in filter.dict().items():
                if value:
                    if counter == 0:
                        delete_statement += " WHERE metadata ->> %s = %s" % (
                            "'" + str(key) + "'",
                            "'" + str(value) + "'",
                        )
                    else:
                        delete_statement += " AND metadata ->> %s = %s" % (
                            str(key),
                            str(value),
                        )
                    counter += 1

            delete_statement += ";"
            try:
                cur.execute(delete_statement)
            except Exception as e:
                print(e)

        if ids:
            delete_statement = "DELETE FROM %s WHERE doc_id IN (%s);" % (
                POSTGRES_TABLENAME,
                ",".join(["'" + str(_id) + "'" for _id in ids]),
            )

            try:
                cur.execute(delete_statement)
            except Exception as e:
                print(e)

        conn.commit()

        cur.close()
        conn.close()

        return True
