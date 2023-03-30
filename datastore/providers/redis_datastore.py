import asyncio
import logging
import os
import re
import json
import redis.asyncio as redis
import numpy as np

from redis.commands.search.query import Query as RediSearchQuery
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import (
    TagField,
    TextField,
    NumericField,
    VectorField,
)
from typing import Dict, List, Optional
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

# Read environment variables for Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
REDIS_INDEX_NAME = os.environ.get("REDIS_INDEX_NAME", "index")
REDIS_DOC_PREFIX = os.environ.get("REDIS_DOC_PREFIX", "doc")
REDIS_DISTANCE_METRIC = os.environ.get("REDIS_DISTANCE_METRIC", "COSINE")
REDIS_INDEX_TYPE = os.environ.get("REDIS_INDEX_TYPE", "FLAT")
assert REDIS_INDEX_TYPE in ("FLAT", "HNSW")

# OpenAI Ada Embeddings Dimension
VECTOR_DIMENSION = 1536

# RediSearch constants
REDIS_REQUIRED_MODULES = ("search", "ReJSON")
REDIS_DEFAULT_ESCAPED_CHARS = re.compile(r"[,.<>{}\[\]\\\"\':;!@#$%^&*()\-+=~\/ ]")
REDIS_SEARCH_SCHEMA = {
    "document_id": TagField("$.document_id", as_name="document_id"),
    "metadata": {
        # "source_id": TagField("$.metadata.source_id", as_name="source_id"),
        "source": TagField("$.metadata.source", as_name="source"),
        # "author": TextField("$.metadata.author", as_name="author"),
        # "created_at": NumericField("$.metadata.created_at", as_name="created_at"),
    },
    "embedding": VectorField(
        "$.embedding",
        REDIS_INDEX_TYPE,
        {
            "TYPE": "FLOAT64",
            "DIM": VECTOR_DIMENSION,
            "DISTANCE_METRIC": REDIS_DISTANCE_METRIC,
            "INITIAL_CAP": 500,
        },
        as_name="embedding",
    ),
}


def unpack_schema(d: dict):
    for v in d.values():
        if isinstance(v, dict):
            yield from unpack_schema(v)
        else:
            yield v


async def _check_redis_module_exist(client: redis.Redis, modules: List[str]) -> bool:
    installed_modules = (await client.info()).get("modules", {"name": ""})
    installed_modules = [m["name"] for m in installed_modules]  # type: ignore
    return all([module in installed_modules for module in modules])


class RedisDataStore(DataStore):
    def __init__(self, client: redis.Redis):
        self.client = client
        # Init default metadata with sentinel values in case the document written has no metadata
        self._default_metadata = {
            field: "_null_" for field in REDIS_SEARCH_SCHEMA["metadata"]
        }

    ### Redis Helper Methods ###

    @classmethod
    async def init(cls):
        """
        Setup the index if it does not exist.
        """
        try:
            # Connect to the Redis Client
            logging.info("Connecting to Redis")
            client = redis.Redis(
                host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD
            )
        except Exception as e:
            logging.error(f"Error setting up Redis: {e}")
            raise e

        if not await _check_redis_module_exist(client, modules=REDIS_REQUIRED_MODULES):  # type: ignore
            raise ValueError(
                "You must add the search and json modules in Redis Stack. "
                "Please refer to Redis Stack docs: https://redis.io/docs/stack/"
            )

        try:
            # Check for existence of RediSearch Index
            await client.ft(REDIS_INDEX_NAME).info()
            logging.info(f"RediSearch index {REDIS_INDEX_NAME} already exists")
        except:
            # Create the RediSearch Index
            logging.info(f"Creating new RediSearch index {REDIS_INDEX_NAME}")
            definition = IndexDefinition(
                prefix=[REDIS_DOC_PREFIX], index_type=IndexType.JSON
            )
            fields = list(unpack_schema(REDIS_SEARCH_SCHEMA))
            await client.ft(REDIS_INDEX_NAME).create_index(
                fields=fields, definition=definition
            )
        return cls(client)

    @staticmethod
    def _redis_key(document_id: str, chunk_id: str) -> str:
        """
        Create the JSON key for document chunks in Redis.

        Args:
            document_id (str): Document Identifier
            chunk_id (str): Chunk Identifier

        Returns:
            str: JSON key string.
        """
        return f"doc:{document_id}:chunk:{chunk_id}"

    @staticmethod
    def _escape(value: str) -> str:
        """
        Escape filter value.

        Args:
            value (str): Value to escape.

        Returns:
            str: Escaped filter value for RediSearch.
        """

        def escape_symbol(match) -> str:
            value = match.group(0)
            return f"\\{value}"

        return REDIS_DEFAULT_ESCAPED_CHARS.sub(escape_symbol, value)

    def _get_redis_chunk(self, chunk: DocumentChunk) -> dict:
        """
        Convert DocumentChunk into a JSON object for storage
        in Redis.

        Args:
            chunk (DocumentChunk): Chunk of a Document.

        Returns:
            dict: JSON object for storage in Redis.
        """
        # Convert chunk -> dict
        data = chunk.__dict__
        metadata = chunk.metadata.__dict__
        data["chunk_id"] = data.pop("id")

        # Prep Redis Metadata
        redis_metadata = dict(self._default_metadata)
        if metadata:
            for field, value in metadata.items():
                if value:
                    if field == "created_at":
                        redis_metadata[field] = to_unix_timestamp(value)  # type: ignore
                    else:
                        redis_metadata[field] = value
        data["metadata"] = redis_metadata
        return data

    def _get_redis_query(self, query: QueryWithEmbedding) -> RediSearchQuery:
        """
        Convert a QueryWithEmbedding into a RediSearchQuery.

        Args:
            query (QueryWithEmbedding): Search query.

        Returns:
            RediSearchQuery: Query for RediSearch.
        """
        filter_str: str = ""

        # RediSearch field type to query string
        def _typ_to_str(typ, field, value) -> str:  # type: ignore
            if isinstance(typ, TagField):
                return f"@{field}:{{{self._escape(value)}}} "
            elif isinstance(typ, TextField):
                return f"@{field}:{self._escape(value)} "
            elif isinstance(typ, NumericField):
                num = to_unix_timestamp(value)
                match field:
                    case "start_date":
                        return f"@{field}:[{num} +inf] "
                    case "end_date":
                        return f"@{field}:[-inf {num}] "

        # Build filter
        if query.filter:
            for field, value in query.filter.__dict__.items():
                if not value:
                    continue
                if field in REDIS_SEARCH_SCHEMA:
                    filter_str += _typ_to_str(REDIS_SEARCH_SCHEMA[field], field, value)
                elif field in REDIS_SEARCH_SCHEMA["metadata"]:
                    if field == "source":  # handle the enum
                        value = value.value
                    filter_str += _typ_to_str(
                        REDIS_SEARCH_SCHEMA["metadata"][field], field, value
                    )
                elif field in ["start_date", "end_date"]:
                    filter_str += _typ_to_str(
                        REDIS_SEARCH_SCHEMA["metadata"]["created_at"], field, value
                    )

        # Postprocess filter string
        filter_str = filter_str.strip()
        filter_str = filter_str if filter_str else "*"

        # Prepare query string
        query_str = (
            f"({filter_str})=>[KNN {query.top_k} @embedding $embedding as score]"
        )
        return (
            RediSearchQuery(query_str)
            .sort_by("score")
            .paging(0, query.top_k)
            .dialect(2)
        )

    async def _redis_delete(self, keys: List[str]):
        """
        Delete a list of keys from Redis.

        Args:
            keys (List[str]): List of keys to delete.
        """
        # Delete the keys
        await asyncio.gather(*[self.client.delete(key) for key in keys])

    #######

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        # Initialize a list of ids to return
        doc_ids: List[str] = []

        # Loop through the dict items
        for doc_id, chunk_list in chunks.items():

            # Append the id to the ids list
            doc_ids.append(doc_id)

            # Write all chunks associated with a document
            n = min(len(chunk_list), 50)
            semaphore = asyncio.Semaphore(n)

            async def _write(chunk: DocumentChunk):
                async with semaphore:
                    # Get redis key and chunk object
                    key = self._redis_key(doc_id, chunk.id)  # type: ignore
                    data = self._get_redis_chunk(chunk)
                    await self.client.json().set(key, "$", data)

            # Concurrently gather writes
            await asyncio.gather(*[_write(chunk) for i, chunk in enumerate(chunk_list)])
        return doc_ids

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and
        returns a list of query results with matching document chunks and scores.
        """
        # Prepare results object
        results: List[QueryResult] = []

        # Use asyncio for concurrent search
        n = min(len(queries), 50)
        semaphore = asyncio.Semaphore(n)

        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            logging.info(f"Query: {query.query}")
            # Extract Redis query
            redis_query: RediSearchQuery = self._get_redis_query(query)
            # Perform a single query
            async with semaphore:
                embedding = np.array(query.embedding, dtype=np.float64).tobytes()
                # Get vector query response from Redis
                query_response = await self.client.ft(REDIS_INDEX_NAME).search(
                    redis_query, {"embedding": embedding}  # type: ignore
                )
                return query_response

        # Concurrently gather query results
        logging.info(f"Gathering {len(queries)} query results", flush=True)  # type: ignore
        query_responses = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        # Iterate through responses and construct results
        for query, query_response in zip(queries, query_responses):

            # Iterate through nearest neighbor documents
            query_results: List[DocumentChunkWithScore] = []
            for doc in query_response.docs:
                # Create a document chunk with score object with the result data
                doc_json = json.loads(doc.json)
                result = DocumentChunkWithScore(
                    id=doc_json["metadata"]["document_id"],
                    score=doc.score,
                    text=doc_json["text"],
                    metadata=doc_json["metadata"],
                )
                query_results.append(result)

            # Add to overall results
            results.append(QueryResult(query=query.query, results=query_results))
        return results

    async def _find_keys(self, pattern: str) -> List[str]:
        return await self.client.keys(pattern=pattern)

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
        # Delete all vectors from the index if delete_all is True
        if delete_all:
            try:
                logging.info(f"Deleting all documents from index")
                await self.client.ft(REDIS_INDEX_NAME).dropindex(True)
                logging.info(f"Deleted all documents successfully")
                return True
            except Exception as e:
                logging.info(f"Error deleting all documents: {e}")
                raise e

        # Delete by filter
        if filter:
            # TODO - extend this to work with other metadata filters?
            if filter.document_id:
                try:
                    keys = await self._find_keys(
                        f"{REDIS_DOC_PREFIX}:{filter.document_id}:*"
                    )
                    await self._redis_delete(keys)
                    logging.info(f"Deleted document {filter.document_id} successfully")
                except Exception as e:
                    logging.info(f"Error deleting document {filter.document_id}: {e}")
                    raise e

        # Delete by explicit ids (Redis keys)
        if ids:
            try:
                logging.info(f"Deleting document ids {ids}")
                keys = []
                # find all keys associated with the document ids
                for document_id in ids:
                    doc_keys = await self._find_keys(
                        pattern=f"{REDIS_DOC_PREFIX}:{document_id}:*"
                    )
                    keys.extend(doc_keys)
                # delete all keys
                logging.info(f"Deleting {len(keys)} keys from Redis")
                await self._redis_delete(keys)
            except Exception as e:
                logging.info(f"Error deleting ids: {e}")
                raise e

        return True
