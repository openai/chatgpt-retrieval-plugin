import logging
import os

import certifi
import numpy as np
import pymongo

from pymongo.mongo_client import MongoClient
from abc import ABC, abstractmethod

from typing import Dict, List, Optional
from datetime import datetime
from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentMetadataFilter,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)
from services.date import to_unix_timestamp


# Read environment variables for CosmosDB Mongo vCore
AZCOSMOS_API = os.environ.get("AZCOSMOS_API", "mongo-vcore")
AZCOSMOS_CONNSTR = os.environ.get("AZCOSMOS_CONNSTR")
AZCOSMOS_DATABASE_NAME = os.environ.get("AZCOSMOS_DATABASE_NAME")
AZCOSMOS_CONTAINER_NAME = os.environ.get("AZCOSMOS_CONTAINER_NAME")
assert AZCOSMOS_API is not None
assert AZCOSMOS_CONNSTR is not None
assert AZCOSMOS_DATABASE_NAME is not None
assert AZCOSMOS_CONTAINER_NAME is not None

# OpenAI Ada Embeddings Dimension
VECTOR_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", 256))


# Abstract class similar to the original data store that allows API level abstraction
class AzureCosmosDBStoreApi(ABC):
    @abstractmethod
    async def ensure(self, num_lists, similarity):
        raise NotImplementedError

    @abstractmethod
    async def upsert_core(self, docId: str, chunks: List[DocumentChunk]) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    async def query_core(
        self, query: QueryWithEmbedding
    ) -> List[DocumentChunkWithScore]:
        raise NotImplementedError

    @abstractmethod
    async def drop_container(self):
        raise NotImplementedError

    @abstractmethod
    async def delete_filter(self, filter: DocumentMetadataFilter):
        raise NotImplementedError

    @abstractmethod
    async def delete_ids(self, ids: List[str]):
        raise NotImplementedError

    @abstractmethod
    async def delete_document_ids(self, documentIds: List[str]):
        raise NotImplementedError


class MongoStoreApi(AzureCosmosDBStoreApi):
    def __init__(self, mongoClient: MongoClient):
        self.mongoClient = mongoClient

    @staticmethod
    def _get_metadata_filter(filter: DocumentMetadataFilter) -> dict:
        returnedFilter: dict = {}
        if filter.document_id is not None:
            returnedFilter["document_id"] = filter.document_id
        if filter.author is not None:
            returnedFilter["metadata.author"] = filter.author
        if filter.start_date is not None:
            returnedFilter["metadata.created_at"] = {
                "$gt": datetime.fromisoformat(filter.start_date)
            }
        if filter.end_date is not None:
            returnedFilter["metadata.created_at"] = {
                "$lt": datetime.fromisoformat(filter.end_date)
            }
        if filter.source is not None:
            returnedFilter["metadata.source"] = filter.source
        if filter.source_id is not None:
            returnedFilter["metadata.source_id"] = filter.source_id
        return returnedFilter

    async def ensure(self, num_lists, similarity):
        assert self.mongoClient.is_mongos
        self.collection = self.mongoClient[AZCOSMOS_DATABASE_NAME][
            AZCOSMOS_CONTAINER_NAME
        ]

        indexes = self.collection.index_information()
        if indexes.get("embedding_cosmosSearch") is None:
            # Ensure the vector index exists.
            indexDefs: List[any] = [
                {
                    "name": "embedding_cosmosSearch",
                    "key": {"embedding": "cosmosSearch"},
                    "cosmosSearchOptions": {
                        "kind": "vector-ivf",
                        "numLists": num_lists,
                        "similarity": similarity,
                        "dimensions": VECTOR_DIMENSION,
                    },
                }
            ]
            self.mongoClient[AZCOSMOS_DATABASE_NAME].command(
                "createIndexes", AZCOSMOS_CONTAINER_NAME, indexes=indexDefs
            )

    async def upsert_core(self, docId: str, chunks: List[DocumentChunk]) -> List[str]:
        # Until nested doc embedding support is done, treat each chunk as a separate doc.
        doc_ids: List[str] = []
        for chunk in chunks:
            finalDocChunk: dict = {
                "_id": f"doc:{docId}:chunk:{chunk.id}",
                "document_id": docId,
                "embedding": chunk.embedding,
                "text": chunk.text,
                "metadata": chunk.metadata.__dict__,
            }

            if chunk.metadata.created_at is not None:
                finalDocChunk["metadata"]["created_at"] = datetime.fromisoformat(
                    chunk.metadata.created_at
                )
            self.collection.insert_one(finalDocChunk)
            doc_ids.append(finalDocChunk["_id"])
        return doc_ids

    async def query_core(
        self, query: QueryWithEmbedding
    ) -> List[DocumentChunkWithScore]:
        pipeline = [
            {
                "$search": {
                    "cosmosSearch": {
                        "vector": query.embedding,
                        "path": "embedding",
                        "k": query.top_k,
                    },
                    "returnStoredSource": True,
                }
            },
            {
                "$project": {
                    "similarityScore": {"$meta": "searchScore"},
                    "document": "$$ROOT",
                }
            },
        ]

        # TODO: Add in match filter (once it can be satisfied).
        # Perform vector search
        query_results: List[DocumentChunkWithScore] = []
        for aggResult in self.collection.aggregate(pipeline):
            finalMetadata = aggResult["document"]["metadata"]
            if finalMetadata["created_at"] is not None:
                finalMetadata["created_at"] = datetime.isoformat(
                    finalMetadata["created_at"]
                )
            result = DocumentChunkWithScore(
                id=aggResult["_id"],
                score=aggResult["similarityScore"],
                text=aggResult["document"]["text"],
                metadata=finalMetadata,
            )
            query_results.append(result)
        return query_results

    async def drop_container(self):
        self.collection.drop()

    async def delete_filter(self, filter: DocumentMetadataFilter):
        delete_filter = self._get_metadata_filter(filter)
        self.collection.delete_many(delete_filter)

    async def delete_ids(self, ids: List[str]):
        self.collection.delete_many({"_id": {"$in": ids}})

    async def delete_document_ids(self, documentIds: List[str]):
        self.collection.delete_many({"document_id": {"$in": documentIds}})


# Datastore implementation.
"""
A class representing a memory store for Azure CosmosDB DataStore, currently only supports Mongo vCore
"""


class AzureCosmosDBDataStore(DataStore):
    def __init__(self, cosmosStore: AzureCosmosDBStoreApi):
        self.cosmosStore = cosmosStore

    """
    Creates a new datastore based on the Cosmos Api provided in the environment variables, 
    only supports Mongo vCore for now
    
    Args:
        numLists (int)   : This integer is the number of clusters that the inverted file (IVF) index 
                                  uses to group the vector data. We recommend that numLists is set to 
                                  documentCount/1000 for up to 1 million documents and to sqrt(documentCount) 
                                  for more than 1 million documents. Using a numLists value of 1 is akin to 
                                  performing brute-force search, which has limited performance.
        similarity (str) : Similarity metric to use with the IVF index. Possible options are COS (cosine distance),
                           L2 (Euclidean distance), and IP (inner product). 
                      
    """

    @staticmethod
    async def create(num_lists, similarity) -> DataStore:
        # Create underlying data store based on the API definition.
        # Right now this only supports Mongo, but set up to support more.
        apiStore: AzureCosmosDBStoreApi = None
        if AZCOSMOS_API == "mongo-vcore":
            mongoClient = MongoClient(AZCOSMOS_CONNSTR)
            apiStore = MongoStoreApi(mongoClient)
        else:
            raise NotImplementedError

        await apiStore.ensure(num_lists, similarity)
        store = AzureCosmosDBDataStore(apiStore)
        return store

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        # Initialize a list of ids to return
        doc_ids: List[str] = []
        for doc_id, chunk_list in chunks.items():
            returnedIds = await self.cosmosStore.upsert_core(doc_id, chunk_list)
            for returnedId in returnedIds:
                doc_ids.append(returnedId)
        return doc_ids

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and
        returns a list of query results with matching document chunks and scores.
        """
        # Prepare query responses and results object
        results: List[QueryResult] = []

        # Gather query results in a pipeline
        logging.info(f"Gathering {len(queries)} query results", flush=True)
        for query in queries:
            logging.info(f"Query: {query.query}")
            query_results = await self.cosmosStore.query_core(query)

            # Add to overall results
            results.append(QueryResult(query=query.query, results=query_results))
        return results

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Returns whether the operation was successful.
        """
        if delete_all:
            # fast path - truncate/delete all items.
            await self.cosmosStore.drop_container()
            return True

        if filter:
            if filter.document_id is not None:
                await self.cosmosStore.delete_document_ids([filter.document_id])
            else:
                await self.cosmosStore.delete_filter(filter)

        if ids:
            await self.cosmosStore.delete_ids(ids)

        return True
