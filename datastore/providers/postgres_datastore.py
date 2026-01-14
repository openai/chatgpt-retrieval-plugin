import os
from typing import Any, List
from datetime import datetime
import numpy as np

from psycopg2 import connect
from psycopg2.extras import DictCursor
from pgvector.psycopg2 import register_vector

from services.date import to_unix_timestamp
from datastore.providers.pgvector_datastore import PGClient, PgVectorDataStore
from models.models import (
    DocumentMetadataFilter,
)

PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", 5432))
PG_DB = os.environ.get("PG_DB", "postgres")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")


# class that implements the DataStore interface for Postgres Datastore provider
class PostgresDataStore(PgVectorDataStore):
    def create_db_client(self):
        return PostgresClient()


class PostgresClient(PGClient):
    def __init__(self) -> None:
        super().__init__()
        self.client = connect(
            dbname=PG_DB, user=PG_USER, password=PG_PASSWORD, host=PG_HOST, port=PG_PORT
        )
        register_vector(self.client)

    def __del__(self):
        # close the connection when the client is destroyed
        self.client.close()

    async def upsert(self, table: str, json: dict[str, Any]):
        """
        Takes in a list of documents and inserts them into the table.
        """
        # Validate table name to prevent SQL injection (only allow alphanumeric and underscore)
        if not table.replace('_', '').isalnum():
            raise ValueError(f"Invalid table name: {table}")

        with self.client.cursor() as cur:
            if not json.get("created_at"):
                json["created_at"] = datetime.now()
            json["embedding"] = np.array(json["embedding"])
            cur.execute(
                f"INSERT INTO {table} (id, content, embedding, document_id, source, source_id, url, author, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET content = %s, embedding = %s, document_id = %s, source = %s, source_id = %s, url = %s, author = %s, created_at = %s",
                (
                    json["id"],
                    json["content"],
                    json["embedding"],
                    json["document_id"],
                    json["source"],
                    json["source_id"],
                    json["url"],
                    json["author"],
                    json["created_at"],
                    json["content"],
                    json["embedding"],
                    json["document_id"],
                    json["source"],
                    json["source_id"],
                    json["url"],
                    json["author"],
                    json["created_at"],
                ),
            )
            self.client.commit()

    async def rpc(self, function_name: str, params: dict[str, Any]):
        """
        Calls a stored procedure in the database with the given parameters.
        """
        data = []
        params["in_embedding"] = np.array(params["in_embedding"])
        with self.client.cursor(cursor_factory=DictCursor) as cur:
            cur.callproc(function_name, params)
            rows = cur.fetchall()
            self.client.commit()
            for row in rows:
                row["created_at"] = to_unix_timestamp(row["created_at"])
                data.append(dict(row))
        return data

    async def delete_like(self, table: str, column: str, pattern: str):
        """
        Deletes rows in the table that match the pattern.
        """
        # Validate table and column names to prevent SQL injection
        if not table.replace('_', '').isalnum():
            raise ValueError(f"Invalid table name: {table}")
        if not column.replace('_', '').isalnum():
            raise ValueError(f"Invalid column name: {column}")

        with self.client.cursor() as cur:
            cur.execute(
                f"DELETE FROM {table} WHERE {column} LIKE %s",
                (f"%{pattern}%",),
            )
            self.client.commit()

    async def delete_in(self, table: str, column: str, ids: List[str]):
        """
        Deletes rows in the table that match the ids.
        """
        # Validate table and column names to prevent SQL injection
        if not table.replace('_', '').isalnum():
            raise ValueError(f"Invalid table name: {table}")
        if not column.replace('_', '').isalnum():
            raise ValueError(f"Invalid column name: {column}")

        with self.client.cursor() as cur:
            cur.execute(
                f"DELETE FROM {table} WHERE {column} IN %s",
                (tuple(ids),),
            )
            self.client.commit()

    async def delete_by_filters(self, table: str, filter: DocumentMetadataFilter):
        """
        Deletes rows in the table that match the filter.
        """
        # Validate table name to prevent SQL injection (only allow alphanumeric and underscore)
        if not table.replace('_', '').isalnum():
            raise ValueError(f"Invalid table name: {table}")

        conditions = []
        params = []

        if filter.document_id:
            conditions.append("document_id = %s")
            params.append(filter.document_id)
        if filter.source:
            conditions.append("source = %s")
            params.append(filter.source)
        if filter.source_id:
            conditions.append("source_id = %s")
            params.append(filter.source_id)
        if filter.author:
            conditions.append("author = %s")
            params.append(filter.author)
        if filter.start_date:
            conditions.append("created_at >= %s")
            params.append(filter.start_date)
        if filter.end_date:
            conditions.append("created_at <= %s")
            params.append(filter.end_date)

        if not conditions:
            return  # No filters specified, don't delete anything

        where_clause = " AND ".join(conditions)
        query = f"DELETE FROM {table} WHERE {where_clause}"

        with self.client.cursor() as cur:
            cur.execute(query, tuple(params))
            self.client.commit()
