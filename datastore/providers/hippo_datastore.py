from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from tenacity import retry, wait_random_exponential, stop_after_attempt
import asyncio
from loguru import logger
from transwarp_hippo_api.hippo_client import HippoClient, HippoField
from transwarp_hippo_api.hippo_type import HippoType, IndexType, MetricType

from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from services.date import to_unix_timestamp

# Read environment variables for hippo configuration

HIPPO_TABLE = os.environ.get("HIPPO_TABLE")
HIPPO_DATABASE = os.environ.get("HIPPO_DATABASE")
HIPPO_HOST = os.environ.get("HIPPO_HOST")
HIPPO_PORT = os.environ.get("HIPPO_PORT")
HIPPO_USER = os.environ.get("HIPPO_USER")
HIPPO_PASSWORD = os.environ.get("HIPPO_PASSWORD")
EMBEDDING_FIELD = os.environ.get("EMBEDDING_FIELD")

if HIPPO_DATABASE is None:
    HIPPO_DATABASE = "default"

if HIPPO_USER is None:
    HIPPO_USER = "shiva"

if HIPPO_PASSWORD is None:
    HIPPO_PASSWORD = "shiva"

if EMBEDDING_FIELD is None:
    EMBEDDING_FIELD = "vector"

assert HIPPO_TABLE is not None
assert HIPPO_HOST is not None
assert HIPPO_PORT is not None

# Set the batch size for upserting vectors to Pinecone
UPSERT_BATCH_SIZE = 100


class HippoDataStore(DataStore):
    def __init__(self):
        # 创建HippoClient
        self.client = HippoClient([HIPPO_HOST + ":" + HIPPO_PORT])
        self.table = None
        if self.client.check_table_exists(HIPPO_TABLE, HIPPO_DATABASE):
            # Connect to an existing table with the specified name
            try:
                logger.info(f"Connecting to existing table {HIPPO_TABLE} in {HIPPO_DATABASE}")
                self.table = self.client.get_table(HIPPO_TABLE, HIPPO_DATABASE)
                logger.info(f"Connected to table {HIPPO_TABLE} in {HIPPO_DATABASE} successfully")
            except Exception as e:
                logger.error(f"Error connecting to table {HIPPO_TABLE} in {HIPPO_DATABASE}: {e}")
                raise e
        else:
            fields_to_table = list(DocumentChunkMetadata.__fields__.keys())
            # Create a new index with the specified name, dimension, and metadata configuration
            try:
                logger.info(
                    f"Creating table {HIPPO_TABLE} in {HIPPO_DATABASE} with metadata config {fields_to_table}"
                )
                field = [
                    HippoField("pk", True, HippoType.STRING),
                    # dimensionality of OpenAI ada v2 embeddings
                    HippoField(EMBEDDING_FIELD, False, HippoType.FLOAT_VECTOR, type_params={"dimension": 1536}),
                    HippoField("text", False, HippoType.STRING),
                    HippoField("document_id", False, HippoType.STRING),
                    HippoField("source_id", False, HippoType.STRING),
                    HippoField("source", False, HippoType.STRING),
                    HippoField("url", False, HippoType.STRING),
                    HippoField("created_at", False, HippoType.STRING),
                    HippoField("author", False, HippoType.STRING),
                ]
                self.table = self.client.create_table(name=HIPPO_TABLE, fields=field, auto_id=True,
                                                      database_name=HIPPO_DATABASE)

                self.table.create_index(EMBEDDING_FIELD, "vector_index", IndexType.IVF_FLAT, MetricType.L2,
                                        nlist=10)
                self.table.activate_index("vector_index")
                logger.info(f"Table {HIPPO_TABLE} in {HIPPO_DATABASE} created successfully")
            except Exception as e:
                logger.error(f"Error creating table {HIPPO_TABLE}: {e}")
                raise e

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """Upsert chunks into the datastore.

        Args:
            chunks (Dict[str, List[DocumentChunk]]): A list of DocumentChunks to insert

        Raises:
            e: Error in upserting data.

        Returns:
            List[str]: The document_id's that were inserted.
        """
        # The doc id's to return for the upsert
        doc_ids: List[str] = []
        for doc_id, chunk_list in chunks.items():
            doc_ids.append(doc_id)
            for chunk in chunk_list:
                values = self._get_values(chunk)

                id = values["id"]
                text = values["text"]
                embedding = values["embedding"]
                source = values["source"]
                source_id = values["source_id"]
                url = values["url"]
                create_at = values["created_at"]
                author = values["author"]
                document_id = values["document_id"]

                print(f"id:{id}")
                print(f"text:{text}")
                print(f"embedding:{embedding}")
                print(f"source:{source}")
                print(f"source_id:{source_id}")
                print(f"url:{url}")
                print(f"create_at:{create_at}")
                print(f"author:{author}")
                print(f"document_id:{document_id}")

                result = self.table.insert_rows(
                    [
                        [id],
                        [embedding],
                        [text],
                        [source],
                        [source_id],
                        [url],
                        [create_at],
                        [author],
                        [document_id],
                    ]
                )
                if not result:
                    raise Exception("Inserting data failed")
                else:
                    logger.info(f"id: {id}")
                    logger.info(f"text: {text}")
                    logger.info(f"embedding: {embedding}")
                    logger.info(f"source: {source}")
                    logger.info(f"source_id: {source_id}")
                    logger.info(f"url: {url}")
                    logger.info(f"create_at: {create_at}")
                    logger.info(f"author: {author}")
                    logger.info(f"document_id: {document_id}")

        return doc_ids

    def _get_values(self, chunk: DocumentChunk) -> List[any] | None:
        """Convert the chunk into a list of values to insert whose indexes align with fields.

        Args:
            chunk (DocumentChunk): The chunk to convert.

        Returns:
            List (any): The values to insert.
        """

        # Convert DocumentChunk and its sub models to dict
        values = chunk.dict()
        # Unpack the metadata into the same dict
        meta = values.pop("metadata")
        values.update(meta)

        # Convert date to int timestamp form
        if values["created_at"]:
            values["created_at"] = to_unix_timestamp(values["created_at"])

        # If source exists, change from Source object to the string value it holds
        if values["source"]:
            values["source"] = values["source"].value

        return values

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:

        # Define a helper coroutine that performs a single query and returns a QueryResult
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            print(query)
            logger.debug(f"Query: {query.query}")
            fields = []
            for field in self.client.get_table_schema(HIPPO_TABLE, HIPPO_DATABASE).get("fields"):
                fields.append(field.get("name"))
            try:
                query_response = self.table.query(
                    search_field=EMBEDDING_FIELD,
                    vectors=[query.embedding],
                    output_fields=fields,
                    topk=query.top_k
                )
            except Exception as e:
                logger.error(f"Error querying table: {e}")
                raise e

            try:
                query_results: List[DocumentChunkWithScore] = []
                score_col = "text" + "%scores"
                count = 0
                print(fields)
                print(EMBEDDING_FIELD)
                fields.remove(EMBEDDING_FIELD)
                for items in zip(*[query_response[0][field] for field in fields]):
                    meta = {field: value for field, value in zip(fields, items)}
                    score = query_response[0][score_col][count]
                    id = meta.pop("document_id")
                    text = meta.pop("text")
                    chunk = DocumentChunkWithScore(
                        id=id,
                        score=score,
                        text=text,
                        metadata=DocumentChunkMetadata(**meta),
                    )
                    query_results.append(chunk)
                return QueryResult(query=query.query, results=query_results)
            except Exception as e:
                logger.error("Failed to query, error: {}".format(e))
                return QueryResult(query=query.query, results=[])

        # Use asyncio.gather to run multiple _single_query coroutines concurrently and collect their results
        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        return results

    async def delete(self, ids: Optional[List[str]] = None, filter: Optional[DocumentMetadataFilter] = None,
                     delete_all: Optional[bool] = None) -> bool:
        if delete_all:
            self.client.delete_table(HIPPO_TABLE, HIPPO_DATABASE)
        else:
            for documentId in ids:
                expr = f"document_id = {documentId} "
                result = self.table.delete_rows_by_query(expr=expr)
                if not result:
                    raise Exception("Deleting data failed")
