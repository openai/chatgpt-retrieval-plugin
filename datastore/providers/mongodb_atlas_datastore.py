import arrow
import os
from typing import Dict, List, Any, Optional
from loguru import logger
from math import ceil
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

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
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "default")
MONGODB_COLLECTION = os.environ.get("MONGODB_COLLECTION", "default")
MONGODB_INDEX = os.environ.get("MONGODB_INDEX", "index_name")
OVERSAMPLING_FACTOR = 1.2
VECTOR_SIZE = 1536
UPSERT_BATCH_SIZE = 100


class MongoDBAtlasDataStore(DataStore):

    def __init__(
        self,
        index_name: Optional[str] = None,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: int = VECTOR_SIZE,
        oversampling_factor: float = OVERSAMPLING_FACTOR,
        **kwargs
    ):
        index_name = index_name or MONGODB_INDEX

        self._oversampling_factor = oversampling_factor
        self.vector_size = vector_size

        if not (index_name and isinstance(index_name, str)):
            raise ValueError("Provide a valid index name")
        self.index_name = index_name

        self._database_name = database_name or MONGODB_DATABASE
        self.collection_name = collection_name or MONGODB_COLLECTION

        # TODO: create index when pymongo supports it.
        # self._set_up_index(vector_size, similarity, recreate_index)

    @cached_property
    def client(self):
        return self._connect_to_mongodb_atlas(
            atlas_connection_uri=MONGODB_CONNECTION_URI
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
        logger.info(f"{self.database_name}: {self.collection_name}")
        await self.client[self.database_name][self.collection_name].insert_many(
            documents_to_upsert
        )

        logger.info("Upsert document successfully")

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
            query_result = await self._execute_embedding_query(query)
            results.append(query_result)

        return results

    async def _execute_embedding_query(self, query: QueryWithEmbedding) -> QueryResult:
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

        cursor = self.client[self.database_name][self.collection_name].aggregate(pipeline)
        results = [
            self._convert_mongodb_document_to_document_chunk_with_score(doc)
            async for doc in cursor
        ]

        return QueryResult(
            query=query.query,
            results=results,
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
            logger.info("Deleting all documents from collection")
            mg_filter = {}

        # Delete by ids
        elif ids:
            ids = [ObjectId(id_) for id_ in ids]
            logger.info(f"Deleting documents with ids: {ids}")
            mg_filter = {
                "_id": {"$in": ids}
            }

        # Delete by filters
        elif filter:
            mg_filter = self._build_mongo_filter(filter)
            logger.info(f"Deleting documents with filter: {mg_filter}")
        # Do nothing
        else:
            logger.warning("Deleting with no specific criteria.")
            mg_filter = None

        if mg_filter is not None:
            try:
                await self.client[self.database_name][self.collection_name].delete_many(mg_filter)
                logger.info("Deleted documents successfully")
            except Exception as e:
                logger.error(f"Error deleting documents with filter: {mg_filter}")
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
            "id": document_chunk.id,
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
    def _connect_to_mongodb_atlas(atlas_connection_uri: str):
        """
        Establish a connection to MongoDB Atlas.
        """
        client = AsyncIOMotorClient(atlas_connection_uri)
        return client
