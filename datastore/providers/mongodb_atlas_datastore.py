import os
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from loguru import logger
from math import ceil
from bson.objectid import ObjectId
import arrow

from datastore.datastore import DataStore
from functools import cached_property
from models.models import (
    DocumentChunk,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)
from services.date import to_unix_timestamp


MONGODB_CONNECTION_URI = os.environ.get("MONGODB_URI")
MONGODB_USER = os.environ.get("MONGODB_USER")
MONGODB_PASSWORD = os.environ.get("MONGODB_PASSWORD")
MONGODB_HOST = os.environ.get("MONGODB_HOST")
MONGODB_PORT = os.environ.get("MONGODB_PORT")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE")
MONGODB_AUTHMECHANISM = os.environ.get("MONGODB_AUTHMECHANISM")
MONGODB_COLLECTION = os.environ.get("MONGODB_COLLECTION")
MONGODB_INDEX = os.environ.get("MONGODB_INDEX")
OVERSAMPLING_FACTOR = 1.2
VECTOR_SIZE = 1536
UPSERT_BATCH_SIZE = 100


class MongoDBAtlasDataStore(DataStore):
    DEFAULT_COLLECTION = "default"

    def __init__(
        self,
        index_name: Optional[str] = MONGODB_INDEX,
        database_name: Optional[str] = MONGODB_DATABASE,
        collection_name: Optional[str] = MONGODB_COLLECTION,
        vector_size: int = VECTOR_SIZE,
        oversampling_factor: float = OVERSAMPLING_FACTOR,
        **kwargs
    ):
        self._oversampling_factor = oversampling_factor
        self.vector_size = vector_size

        if not (index_name and isinstance(index_name, str)):
            raise ValueError("Provide a valid index name")
        self.index_name = index_name

        self._database_name = database_name
        self._collection_name = collection_name or self.DEFAULT_COLLECTION

        # TODO: create index when pymongo supports it.
        # self._set_up_index(vector_size, similarity, recreate_index)

    @cached_property
    def client(self):
        return self._connect_to_mongodb_atlas(
            atlas_connection_uri=MONGODB_CONNECTION_URI,
            host=MONGODB_USER,
            port=MONGODB_PASSWORD,
            username=MONGODB_HOST,
            password=MONGODB_PORT,
            auth_source=self._database_name,
            auth_mechanism=MONGODB_AUTHMECHANISM,
        )

    @property
    def database_name(self):
        if not self._database_name:
            self._database_name = self.client.get_default_database()
        return self._database_name

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        documents_to_upsert = []
        for _, chunk_list in chunks.items():
            for chunk in chunk_list:
                documents_to_upsert.append(
                    self._convert_document_chunk_to_mongodb_document(chunk)
                )
        # Upsert documents into the MongoDB collection
        logger.info(f"{self.database_name}: {self._collection_name}")
        self.client[self.database_name][self._collection_name].insert_many(
            documents_to_upsert
        )
        
        return list(chunks.keys())

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns
        a list of query results with matching document chunks and scores.
        """
        results = []
        for query in queries:
            query_result = self.execute_embedding_query(query)
            results.append(query_result)

        return results

    def execute_embedding_query(self, query: QueryWithEmbedding) -> QueryResult:
        """
        Execute a MongoDB query using vector search on the specified collection and
        return the result of the query, including matched documents and their scores.
        """
        pipeline = [
            {
                '$vectorSearch': {
                    'index': self.index_name,
                    'path': 'embedding',
                    'queryVector': query.embedding,
                    'numCandidates': ceil(query.top_k * self._oversampling_factor),
                    'limit': query.top_k
                 }
            }, {
                '$project': {
                    'text': 1,
                    'metadata': 1,
                    'score': {
                        '$meta': 'vectorSearchScore'
                    }
                }
            }
        ]

        results = self.client[self.database_name][self._collection_name].aggregate(pipeline)
        
        return QueryResult(
            query=query.query,
            results=[
                self._convert_mongodb_document_to_document_chunk_with_score(result)
                for result in results
            ],
        )

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes documents by ids, filter, or everything in the datastore.
        Returns whether the operation was successful.
        """

        # Delete all documents from the collection if delete_all is True
        if delete_all:
            try:
                logger.info("Deleting all documents from collection")
                self.client[self.database_name][self._collection_name].delete_many({})
                logger.info("Deleted all documents successfully")
            except Exception as e:
                logger.error(f"Error deleting all documents: {e}")
                raise e

        elif ids:
            ids = [ObjectId(id_) for id_ in ids]  # TODO: check if it is necessary.
            try:
                logger.info(f"Deleting documents with ids: {ids}")
                self.client[self.database_name][self._collection_name].delete_many({
                    "_id": {"$in": ids}
                })
                logger.info("Deleted documents with ids successfully")
            except Exception as e:
                logger.error(f"Error deleting documents with ids: {e}")
                raise e

        else:
            mg_filter = self._build_mongo_filter(filter)
            if mg_filter:
                try:
                    logger.info(f"Deleting documents with filter: {mg_filter}")
                    self.client[self.database_name][self._collection_name].delete_many(mg_filter)
                    logger.info("Deleted documents with filter successfully")
                except Exception as e:
                    logger.info(type(mg_filter))
                    logger.error(f"Error deleting documents with filter: {e}")
                    raise e

        return True

    def _convert_mongodb_document_to_document_chunk_with_score(
        self, document: Dict
    ) -> DocumentChunkWithScore:
        # Convert MongoDB document to DocumentChunkWithScore
        return DocumentChunkWithScore(
            id=str(document["_id"]),
            text=document["text"],
            metadata=document["metadata"],
            score=document["score"],
        )

    def _convert_document_chunk_to_mongodb_document(
        self, document_chunk: DocumentChunk
    ) -> Dict:
        # Convert DocumentChunk to MongoDB document format
        
        created_at = (
            to_unix_timestamp(document_chunk.metadata.created_at)
            if document_chunk.metadata.created_at is not None
            else int(arrow.now().timestamp())
        )
        
        mongodb_document = {
            "text": document_chunk.text,
            "created_at": created_at,
            "metadata": document_chunk.metadata.dict(),
            "embedding": document_chunk.embedding,
        }
        
        return mongodb_document

    def _build_mongo_filter(
        self, filter: Optional[DocumentMetadataFilter] = None
    ) -> Dict[str, Any]:
        """
        Generate MongoDB query filters based on the provided DocumentMetadataFilter.
        """
        if filter is None:
            return {}

        mongo_filters = {
            "$and": [],
        }

        # For each field in the MetadataFilter,
        # check if it has a value and add the corresponding MongoDB filter expression
        for field, value in filter.dict().items():
            if value is not None:
                if field == "start_date":
                    mongo_filters["$and"].append(
                        {"created_at": {"$gte": to_unix_timestamp(value)}}
                    )
                elif field == "end_date":
                    mongo_filters["$and"].append(
                        {"created_at": {"$lte": to_unix_timestamp(value)}}
                    )
                else:
                    mongo_filters["$and"].append(
                        {f"metadata.{field}": value}
                    )

        return mongo_filters

    @staticmethod
    def _connect_to_mongodb_atlas(
            atlas_connection_uri: Optional[str] = None,
            host: Optional[str] = None,
            port: Optional[str] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            auth_source: Optional[str] = None,
            auth_mechanism: Optional[str] = None,
            ):
        """
        Establish a connection to MongoDB Atlas.
        """
        if atlas_connection_uri is not None:
            client = MongoClient(atlas_connection_uri)
        elif host:
            client = MongoClient(
                host=host,
                port=port,
                username=username,
                password=password,
                authSource=auth_source,
                authMechanism=auth_mechanism
            )
        else:
            raise ValueError("Please provide either atlas_connection_uri or mongo credentials.")
        return client
