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
from psycopg_pool import ConnectionPool
import logging
from services.date import to_unix_timestamp

# Read environment variables for Postgres

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5433")
POSTGRES_USERNAME = os.environ.get("POSTGRES_USERNAME", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "pgml_development")
POSTGRES_TABLENAME = os.environ.get("POSTGRES_TABLENAME", "chatgpt_datastore")
POSTGRES_EMBEDDING_INDEX = os.environ.get(
    "POSTGRES_EMBEDDING_INDEX", "chatgpt_datastore_embedding_index"
)
POSTGRES_DOCID_INDEX = os.environ.get(
    "POSTGRES_EMBEDDING_INDEX", "chatgpt_datastore_docid_index"
)
POSTGRES_UPSERT_COMMAND = os.environ.get("POSTGRES_UPSERT_COMMAND", "INSERT")
POSTGRES_MIN_ROWS_FOR_INDEX = int(os.environ.get("POSTGRES_MIN_ROWS_FOR_INDEX", 1000))
POSTGRES_MIN_NEW_ROWS_FOR_REINDEX = int(
    os.environ.get("POSTGRES_MIN_NEW_ROWS_FOR_REINDEX", 1000)
)

assert POSTGRES_UPSERT_COMMAND in ["COPY", "INSERT"]

# OpenAI Ada Embeddings Dimension
VECTOR_DIMENSION = 1536


class PostgresDataStore(DataStore):
    def __init__(self) -> None:
        conninfo = (
            "postgresql://"
            + POSTGRES_USERNAME
            + ":"
            + POSTGRES_PASSWORD
            + "@"
            + POSTGRES_HOST
            + ":"
            + POSTGRES_PORT
            + "/"
            + POSTGRES_DATABASE
        )
        self.pool = ConnectionPool(conninfo)
        conn = self.pool.getconn()
        conn.autocommit = True
        # Insert the vector and text into the database
        logging.info("Creating table %s" % POSTGRES_TABLENAME)
        create_table = (
            "CREATE TABLE IF NOT EXISTS %s (doc_id TEXT, chunk_id TEXT, text TEXT, embedding vector(%s), metadata JSONB)"
            % (POSTGRES_TABLENAME, str(VECTOR_DIMENSION))
        )
        cur = conn.cursor()
        cur.execute(create_table)
        index_exists_staetment = (
            "SELECT EXISTS (SELECT 1 FROM pg_indexes  WHERE tablename = '%s' AND indexname = '%s')"
            % (POSTGRES_TABLENAME, POSTGRES_DOCID_INDEX)
        )
        cur.execute(index_exists_staetment)
        self.docid_index_exists = cur.fetchall()[0][0]

        if not self.docid_index_exists:
            index_doc_ids = (
                "CREATE INDEX CONCURRENTLY ON %s (doc_id) " % POSTGRES_TABLENAME
            )
            cur.execute(index_doc_ids)

        self.index_counter = 0
        index_exists_staetment = (
            "SELECT EXISTS (SELECT 1 FROM pg_indexes  WHERE tablename = '%s' AND indexname = '%s')"
            % (POSTGRES_TABLENAME, POSTGRES_EMBEDDING_INDEX)
        )
        cur.execute(index_exists_staetment)
        self.index_exists = cur.fetchall()[0][0]

        cur.close()
        self.pool.putconn(conn)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict from document id to list of document chunks and inserts them into the index.
        Return a list of document ids.
        """
        # Create a connection

        conn = self.pool.getconn()
        conn.autocommit = True
        cur = conn.cursor()

        # Initialize a list of ids to return
        doc_ids: List[str] = []
        if POSTGRES_UPSERT_COMMAND == "INSERT":
            # Loop through docs/chunks
            for doc_id, chunk_list in chunks.items():
                doc_ids.append(doc_id)
                for chunk in chunk_list:
                    metadata = chunk.metadata.dict()
                    if "created_at" in list(metadata.keys()):
                        if metadata["created_at"]:
                            metadata["created_at"] = to_unix_timestamp(
                                metadata["created_at"]
                            )
                    metadata = json.dumps(metadata)
                    insert_statement = sql.SQL(
                        "INSERT INTO {} (doc_id, chunk_id, text, embedding, metadata) VALUES ({}, {}, {}, {}, {})"
                    ).format(
                        sql.Identifier(POSTGRES_TABLENAME),
                        sql.Literal(doc_id),
                        sql.Literal(chunk.id),
                        sql.Literal(chunk.text),
                        sql.Literal(chunk.embedding),
                        sql.Literal(metadata),
                    )
                    cur.execute(insert_statement)
                    self.index_counter += 1

        if POSTGRES_UPSERT_COMMAND == "COPY":
            with cur.copy(
                "COPY %s (doc_id, chunk_id, text, embedding, metadata) FROM STDIN"
                % POSTGRES_TABLENAME
            ) as copy:
                for doc_id, chunk_list in chunks.items():
                    doc_ids.append(doc_id)
                    for chunk in chunk_list:
                        text = sql.Literal(chunk.text).as_string(conn)
                        embedding = (
                            "[" + ",".join([str(v) for v in chunk.embedding]) + "]"
                        )

                        metadata = chunk.metadata.dict()
                        if "created_at" in list(metadata.keys()):
                            if metadata["created_at"]:
                                metadata["created_at"] = to_unix_timestamp(
                                    metadata["created_at"]
                                )
                        metadata = json.dumps(metadata)

                        row = (doc_id, chunk.id, text, embedding, metadata)
                        copy.write_row(row)
                        self.index_counter += 1

        cur.execute("SELECT COUNT(*) from %s" % POSTGRES_TABLENAME)
        nrows = cur.fetchall()[0][0]

        if self.index_exists:
            if self.index_counter > POSTGRES_MIN_NEW_ROWS_FOR_REINDEX:
                reindex_statement = "REINDEX INDEX CONCURRENTLY %s" % (
                    POSTGRES_EMBEDDING_INDEX
                )
                cur.execute(reindex_statement)
                print(
                    "Reindex initiated when nrows = %d, index counter = %d"
                    % (nrows, self.index_counter)
                )
                self.index_counter = 0

        else:
            if nrows > POSTGRES_MIN_ROWS_FOR_INDEX:
                index_statement = (
                    "CREATE INDEX CONCURRENTLY %s ON %s USING ivfflat (embedding vector_cosine_ops)"
                    % (POSTGRES_EMBEDDING_INDEX, POSTGRES_TABLENAME)
                )
                cur.execute(index_statement)
                self.index_exists = True
                print("Created index if not exists when nrows = %d" % nrows)
                self.index_counter = 0

        cur.close()
        self.pool.putconn(conn)

        return doc_ids

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and
        returns a list of query results with matching document chunks and scores.
        """
        # Prepare query responses and results object
        results: List[QueryResult] = []

        # Create a connection
        conn = self.pool.getconn()
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

        conn.commit()
        cur.close()
        self.pool.putconn(conn)

        return results

    async def delete(
        self,
        ids: List[str] | None = None,
        filter: DocumentMetadataFilter | None = None,
        delete_all: bool | None = None,
    ) -> bool:
        # Create a connection
        conn = self.pool.getconn()
        cur = conn.cursor()

        if delete_all:
            delete_statement = "TRUNCATE %s" % (POSTGRES_TABLENAME)
            try:
                cur.execute(delete_statement)
            except Exception as e:
                print(e)

        if filter:
            start_date = None
            end_date = None

            if "start_date" in filter.dict().keys():
                start_date = filter.dict().pop("start_date")
                if start_date:
                    start_date = to_unix_timestamp(start_date)

            if "end_date" in filter.dict().keys():
                end_date = filter.dict().pop("end_date")
                if end_date:
                    end_date = to_unix_timestamp(end_date)

            if start_date and end_date:
                delete_statement = "DELETE FROM %s" % POSTGRES_TABLENAME
                delete_statement += " WHERE metadata --> created_at > %d " % start_date
                delete_statement += " AND metadata --> created_at < %d " % end_date
                try:
                    cur.execute(delete_statement)
                except Exception as e:
                    print(e)
            else:
                if start_date:
                    delete_statement = "DELETE FROM %s" % POSTGRES_TABLENAME
                    delete_statement += (
                        " WHERE metadata --> created_at > %d " % start_date
                    )
                    try:
                        cur.execute(delete_statement)
                    except Exception as e:
                        print(e)
                if end_date:
                    delete_statement = "DELETE FROM %s" % POSTGRES_TABLENAME
                    delete_statement += (
                        " WHERE metadata --> created_at < %d " % end_date
                    )
                    try:
                        cur.execute(delete_statement)
                    except Exception as e:
                        print(e)

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
        self.pool.putconn(conn)

        return True
