import os
from typing import Dict, List, Any, Optional
from loguru import logger
from importlib.metadata import version
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.driver_info import DriverInfo
from pymongo import UpdateOne

from datastore.datastore import DataStore
from functools import cached_property
from models.models import (
    Document,
    DocumentChunk,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)
from services.chunks import get_document_chunks
from services.date import to_unix_timestamp


MONGODB_CONNECTION_URI = os.environ.get("MONGODB_URI")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "default")
MONGODB_COLLECTION = os.environ.get("MONGODB_COLLECTION", "default")
MONGODB_INDEX = os.environ.get("MONGODB_INDEX", "default")
OVERSAMPLING_FACTOR = 10
MAX_CANDIDATES = 10_000


class MongoDBAtlasDataStore(DataStore):

    def __init__(
        self,
        atlas_connection_uri: str = MONGODB_CONNECTION_URI,
        index_name: str = MONGODB_INDEX,
        database_name: str = MONGODB_DATABASE,
        collection_name: str = MONGODB_COLLECTION,
        oversampling_factor: float = OVERSAMPLING_FACTOR,
    ):
        """
        Initialize a MongoDBAtlasDataStore instance.

        Parameters:
        - index_name (str, optional): Vector search index. If not provided, default index name is used.
        - database_name (str, optional): Database. If not provided, default database name is used.
        - collection_name (str, optional): Collection. If not provided, default collection name is used.
        - oversampling_factor (float, optional): Oversampling factor for data augmentation.
                                                 Default is OVERSAMPLING_FACTOR.

        Raises:
        - ValueError: If index_name is not a valid string.

        Attributes:
        - index_name (str): Name of the index.
        - database_name (str): Name of the database.
        - collection_name (str): Name of the collection.
        - oversampling_factor (float): Oversampling factor for data augmentation.
        """

        self.atlas_connection_uri = atlas_connection_uri
        self.oversampling_factor = oversampling_factor
        self.database_name = database_name
        self.collection_name = collection_name

        if not (index_name and isinstance(index_name, str)):
            raise ValueError("Provide a valid index name")
        self.index_name = index_name

        # TODO: Create index via driver https://jira.mongodb.org/browse/PYTHON-4175
        # self._create_search_index(num_dimensions=1536, path="embedding", similarity="dotProduct", type="vector")

    @cached_property
    def client(self):
        return self._connect_to_mongodb_atlas(
            atlas_connection_uri=MONGODB_CONNECTION_URI
        )

    async def upsert(
        self, documents: List[Document], chunk_token_size: Optional[int] = None
    ) -> List[str]:
        """
        Takes in a list of Documents, chunks them, and upserts the chunks into the database.
        Return a list the ids of the document chunks.
        """
        chunks = get_document_chunks(documents, chunk_token_size)
        return await self._upsert(chunks)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        documents_to_upsert = []
        inserted_ids = []
        for chunk_list in chunks.values():
            for chunk in chunk_list:
                inserted_ids.append(chunk.id)
                documents_to_upsert.append(
                        UpdateOne({'_id': chunk.id}, {"$set": chunk.dict()}, upsert=True)
                )
        logger.info(f"Upsert documents into MongoDB collection: {self.database_name}: {self.collection_name}")
        await self.client[self.database_name][self.collection_name].bulk_write(documents_to_upsert)
        logger.info("Upsert successful")

        return inserted_ids

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
                    'numCandidates': min(query.top_k * self.oversampling_factor, MAX_CANDIDATES),
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

        async with self.client[self.database_name][self.collection_name].aggregate(pipeline) as cursor:
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

        Note that ids refer to those in the datastore,
        which are those of the **DocumentChunks**
        """
        # Delete all documents from the collection if delete_all is True
        if delete_all:
            logger.info("Deleting all documents from collection")
            mg_filter = {}

        # Delete by ids
        elif ids:
            logger.info(f"Deleting documents with ids: {ids}")
            mg_filter = {"_id": {"$in": ids}}

        # Delete by filters
        elif filter:
            mg_filter = self._build_mongo_filter(filter)
            logger.info(f"Deleting documents with filter: {mg_filter}")
        # Do nothing
        else:
            logger.warning("No criteria set; nothing to delete args: ids: %s, filter: %s delete_all: %s", ids, filter, delete_all)
            return True

        try:
            await self.client[self.database_name][self.collection_name].delete_many(mg_filter)
            logger.info("Deleted documents successfully")
        except Exception as e:
            logger.error("Error deleting documents with filter: %s -- error: %s", mg_filter, e)
            return False

        return True

    def _convert_mongodb_document_to_document_chunk_with_score(
        self, document: Dict
    ) -> DocumentChunkWithScore:
        # Convert MongoDB document to DocumentChunkWithScore
        return DocumentChunkWithScore(
            id=document.get("_id"),
            text=document["text"],
            metadata=document.get("metadata"),
            score=document.get("score"),
        )

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

        client = AsyncIOMotorClient(
            atlas_connection_uri,
            driver=DriverInfo(name="Chatgpt Retrieval Plugin", version=version("chatgpt_retrieval_plugin")))
        return client
