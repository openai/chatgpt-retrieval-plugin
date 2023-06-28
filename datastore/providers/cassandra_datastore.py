import os
import base64
import time
from typing import Any, List, Dict, Optional
from datetime import datetime
import numpy as np
from cassandra import ConsistencyLevel
import zipfile
import json
import requests
from loguru import logger

from cassandra.cluster import Cluster, NoHostAvailable
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement, ValueSequence

from services.date import to_unix_timestamp
from models.models import (
    DocumentMetadataFilter,
    DocumentChunk, QueryWithEmbedding, QueryResult, DocumentChunkWithScore, DocumentChunkMetadata,
)

CASSANDRA_HOST = os.environ.get("CASSANDRA_HOST", "localhost")
CASSANDRA_PORT = int(os.environ.get("CASSANDRA_PORT", 9042))
CASSANDRA_KEYSPACE = os.environ.get("CASSANDRA_KEYSPACE", "cassandra")
CASSANDRA_USER = os.environ.get("CASSANDRA_USER", "cassandra")
CASSANDRA_PASSWORD = os.environ.get("CASSANDRA_PASSWORD", "cassandra")
ASTRA_BUNDLE = os.environ.get("ASTRA_BUNDLE", None)


# class that implements the DataStore interface for Cassandra Datastore provider
class CassandraDataStore():
    def __init__(self):
        self.client = self.create_db_client()
    def create_db_client(self):
        return CassandraClient()
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict of document_ids to list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        for document_id, document_chunks in chunks.items():
            for chunk in document_chunks:
                json = {
                    "id": chunk.id,
                    "content": chunk.text,
                    "embedding": chunk.embedding,
                    "document_id": document_id,
                    "source": chunk.metadata.source,
                    "source_id": chunk.metadata.source_id,
                    "url": chunk.metadata.url,
                    "author": chunk.metadata.author,
                }
                if chunk.metadata.created_at:
                    json["created_at"] = (
                        datetime.fromtimestamp(
                            to_unix_timestamp(chunk.metadata.created_at)
                        ),
                    )
                await self.client.upsert("documents", json)

        return list(chunks.keys())


    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        query_results: List[QueryResult] = []
        for query in queries:
            # get the top 3 documents with the highest cosine similarity using rpc function in the database called "match_page_sections"
            params = {
                "in_embedding": query.embedding,
            }
            if not query.top_k:
                query.top_k = 10
            data = await self.client.runQuery(query)

            if data is None:
                query_results.append(QueryResult(query=query.query, results=[]))
            else:
                results: List[DocumentChunkWithScore] = []
                for row in data:
                    doc_metadata = DocumentChunkMetadata(
                        source=row.source,
                        source_id=row.source_id,
                        document_id=row.document_id,
                        url=row.url,
                        created_at=row.created_at.isoformat(),
                        author=row.author,
                    )
                    document_chunk = DocumentChunkWithScore(
                        id=row.id,
                        text=row.content,
                        # TODO: add embedding to the response ?
                        # embedding=row.embedding,
                        score=float(row.score),
                        #score=float(1),
                        metadata=doc_metadata
                    )
                    results.append(document_chunk)
                query_results.append(QueryResult(query=query.query, results=results))
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
        if delete_all:
            try:
                await self.client._delete("documents",delete_all)
            except:
                return False
        elif ids:
            try:
                await self.client._delete_in("documents", "document_id", ids)
            except:
                return False
        elif filter:
            raise NotImplementedError
            #try:
            #    await self.client._delete_by_filters("documents", filter)
            #except:
            #    return False
        return True


class CassandraClient():
    def __init__(self) -> None:
        super().__init__()
        try:
            self.connect()
        except NoHostAvailable as e:
            print(f"No host in the cluster could be contacted: {e}")
            # sleep and retry
            time.sleep(5)
            self.connect()
        self.create_table()


    def connect(self):
        if ASTRA_BUNDLE is not None:
            cloud_config= {
              'secure_connect_bundle': ASTRA_BUNDLE
            }
            auth_provider = PlainTextAuthProvider(CASSANDRA_USER, CASSANDRA_PASSWORD)
            self.cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
            self.session = self.cluster.connect()
        else:
            auth_provider = PlainTextAuthProvider(CASSANDRA_USER, CASSANDRA_PASSWORD)
            self.cluster = Cluster([CASSANDRA_HOST], port= CASSANDRA_PORT, auth_provider=auth_provider)
            self.session = self.cluster.connect()
        # create schema

    def create_table(self):
        try:
            if ASTRA_BUNDLE:
                # Open the zip file
                with zipfile.ZipFile(ASTRA_BUNDLE, 'r') as zip_ref:
                    # Open the JSON file
                    with zip_ref.open('config.json') as json_file:
                        # Load the JSON file
                        data = json.loads(json_file.read().decode('utf-8'))

                # Now `data` is a Python dictionary that contains your JSON data.
                # You can access values in it like you would with any dictionary.
                # For example, to get the value of 'key' in the JSON data:
                host = data['host']

                # databaseID is cf4984cf-4b66-4025-b162-5a951a28777d which can be extracted from host cf4984cf-4b66-4025-b162-5a951a28777d-us-east-1.db.astra-test.datastax.com
                databaseID = "-".join(host.split("-")[:5])

                # Define the URL
                url = f"https://api.astra.datastax.com/v2/databases/{databaseID}/keyspaces/{CASSANDRA_KEYSPACE}"

                # Define the headers
                headers = {
                    "Authorization": f"Bearer {CASSANDRA_PASSWORD}",
                    "Content-Type": "application/json"
                }

                # Define the payload (if any)
                payload = {}

                # Make the POST request
                response = requests.post(url, headers=headers, data=json.dumps(payload)).json()

                # Print the response
                if 'errors' in response:
                    # Handle the errors
                    errors = response['errors']
                    if errors[0]['message']:
                        if errors[0]['message'] == 'JWT not valid':
                          logger.warning("Please use the word `token` and your AstraDB token as CASSANDRA_USER and CASSANDRA_PASSWORD respectively instead of client and secret (starting with `ASTRACS:` to allow dynamic astra keyspace creation")
            else:
                self.session.execute(f"""create keyspace if not exists {CASSANDRA_KEYSPACE} WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1 }};""")

            self.session.execute(f"""create table if not exists {CASSANDRA_KEYSPACE}.documents (
                    id text primary key,
                    source text,
                    source_id text,
                    content text,
                    document_id text,
                    author text,
                    url text,
                    created_at timestamp,
                    embedding VECTOR<float,1536>
            );""")

            statement = SimpleStatement(
                f"CREATE CUSTOM INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.documents (embedding) USING 'StorageAttachedIndex';"
                , consistency_level=ConsistencyLevel.QUORUM
            )
            self.session.execute(statement)

            statement = SimpleStatement(
                f"CREATE CUSTOM INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.documents (document_id) USING 'StorageAttachedIndex';"
                , consistency_level=ConsistencyLevel.QUORUM
            )
            self.session.execute(statement)

            statement = SimpleStatement(
                f"CREATE CUSTOM INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.documents (author) USING 'StorageAttachedIndex';"
                , consistency_level=ConsistencyLevel.QUORUM
            )
            self.session.execute(statement)

            statement = SimpleStatement(
                f"CREATE CUSTOM INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.documents (source) USING 'StorageAttachedIndex';"
                , consistency_level=ConsistencyLevel.QUORUM
            )
            self.session.execute(statement)

            statement = SimpleStatement(
                f"CREATE CUSTOM INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.documents (source_id) USING 'StorageAttachedIndex';"
                , consistency_level=ConsistencyLevel.QUORUM
            )
            self.session.execute(statement)


            statement = SimpleStatement(
                f"CREATE CUSTOM INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.documents (created_at) USING 'StorageAttachedIndex';"
                , consistency_level=ConsistencyLevel.QUORUM
            )
            self.session.execute(statement)


            statement = SimpleStatement(
                f"CREATE CUSTOM INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.documents (url) USING 'StorageAttachedIndex';"
                , consistency_level=ConsistencyLevel.QUORUM
            )
            self.session.execute(statement)
        except Exception as e:
                print(f"Exception creating table or index: {e}")
                exit(1)

    def __del__(self):
        # close the connection when the client is destroyed
        self.cluster.shutdown()

    async def runQuery(self, query):
        filters = ""
        if query.filter:
            filter = query.filter
            #TODO, change to WHERE when syntax changes
            filters = " WHERE "
            if filter.document_id:
                filters += f" document_id = '{filter.document_id}' AND"
            if filter.source:
                filters += f" source = '{filter.source}' AND"
            if filter.source_id:
                filters += f" source_id = '{filter.source_id}' AND"
            if filter.author:
                filters += f" author = '{filter.author}' AND"
            if filter.start_date:
                filters += f" created_at >= '{filter.start_date}' AND"
            if filter.end_date:
                filters += f" created_at <= '{filter.end_date}' AND"
            filters = filters[:-4]

        try:
            queryString = f"""SELECT id, content, embedding, document_id, 
            source, source_id, url, author, created_at, 
            similarity_cosine(?, embedding) as score
            from {CASSANDRA_KEYSPACE}.documents {filters} 
            ORDER BY embedding ann of {query.embedding} 
            LIMIT {query.top_k};"""
            print(queryString)
            statement = self.session.prepare(queryString)
            statement.consistency_level = ConsistencyLevel.QUORUM
            boundStatement = statement.bind([query.embedding])
            resultset = self.session.execute(boundStatement)
            return resultset

        except Exception as e:
            print(f"Exception during query (retrying): {e}")
            #sleep 10 seconds and retry
            time.sleep(10)
            exit(1)
            #await self.runQuery(query)

    async def upsert(self, table: str, json: dict[str, Any]):
        """
        Takes in a list of documents and inserts them into the table.
        """
        if json["source"] is not None:
            json["source"] = json["source"].name
        if not json.get("created_at"):
            json["created_at"] = datetime.now()
        else:
            json["created_at"] = json["created_at"][0]
        json["embedding"] = np.array(json["embedding"])

        try:
            queryString = f"""
                insert into {CASSANDRA_KEYSPACE}.{table} 
                (id, content, embedding, document_id, source, source_id, url, author, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            print(queryString)
            statement = SimpleStatement(queryString, consistency_level=ConsistencyLevel.QUORUM)

            self.session.execute(statement, (json["id"],
                                             json["content"],
                                             json["embedding"].tolist(),
                                             json["document_id"],
                                             json["source"],
                                             json["source_id"],
                                             json["url"],
                                             json["author"],
                                             json["created_at"])
                                 )
        except Exception as e:
            print(f"Exception inserting into table: {e}")
            exit(1)

    async def _delete_by_filters(self, table: str, filter: DocumentMetadataFilter):
        """
        Deletes rows in the table that match the filter.
        """

        filters = "WHERE"
        if filter.document_id:
            filters += f" document_id = '{filter.document_id}' AND"
        if filter.source:
            filters += f" source = '{filter.source}' AND"
        if filter.source_id:
            filters += f" source_id = '{filter.source_id}' AND"
        if filter.author:
            filters += f" author = '{filter.author}' AND"
        if filter.start_date:
            filters += f" created_at >= '{filter.start_date}' AND"
        if filter.end_date:
            filters += f" created_at <= '{filter.end_date}' AND"
        filters = filters[:-4]
        self.session.execute(f"DELETE FROM {table} {filters}")

    async def _delete(self, table, delete_all):
        if delete_all:
            self.session.execute(f"TRUNCATE TABLE {CASSANDRA_KEYSPACE}.{table}")
        else:
            raise NotImplementedError


    async def _delete_in(self, table: str, column: str, doc_ids: List[str]):
        """
        Deletes rows in the table that match the ids.
        """
        try:
            query = f"SELECT id FROM {CASSANDRA_KEYSPACE}.{table} WHERE {column} IN (%s)"
            statement = SimpleStatement(query, consistency_level=ConsistencyLevel.QUORUM)
            parameters = ValueSequence(doc_ids)
            rows = self.session.execute(
                statement,
                parameters
            )

            ids = ValueSequence([row.id for row in rows])

            self.session.execute(
                f"DELETE FROM {CASSANDRA_KEYSPACE}.{table} WHERE id IN (%s)",
                ids
            )
        except Exception as e:
            print(f"Exception deleting from table: {e}")
            exit(1)