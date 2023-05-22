import asyncio
import os
import re
import uuid
from typing import Dict, List, Optional

import weaviate
from loguru import logger
from weaviate import Client
from weaviate.util import generate_uuid5

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

WEAVIATE_URL_DEFAULT = "http://localhost:8080"
WEAVIATE_CLASS = os.environ.get("WEAVIATE_CLASS", "OpenAIDocument")

WEAVIATE_BATCH_SIZE = int(os.environ.get("WEAVIATE_BATCH_SIZE", 20))
WEAVIATE_BATCH_DYNAMIC = os.environ.get("WEAVIATE_BATCH_DYNAMIC", False)
WEAVIATE_BATCH_TIMEOUT_RETRIES = int(os.environ.get("WEAVIATE_TIMEOUT_RETRIES", 3))
WEAVIATE_BATCH_NUM_WORKERS = int(os.environ.get("WEAVIATE_BATCH_NUM_WORKERS", 1))

SCHEMA = {
    "class": WEAVIATE_CLASS,
    "description": "The main class",
    "properties": [
        {
            "name": "chunk_id",
            "dataType": ["string"],
            "description": "The chunk id",
        },
        {
            "name": "document_id",
            "dataType": ["string"],
            "description": "The document id",
        },
        {
            "name": "text",
            "dataType": ["text"],
            "description": "The chunk's text",
        },
        {
            "name": "source",
            "dataType": ["string"],
            "description": "The source of the data",
        },
        {
            "name": "source_id",
            "dataType": ["string"],
            "description": "The source id",
        },
        {
            "name": "url",
            "dataType": ["string"],
            "description": "The source url",
        },
        {
            "name": "created_at",
            "dataType": ["date"],
            "description": "Creation date of document",
        },
        {
            "name": "author",
            "dataType": ["string"],
            "description": "Document author",
        },
    ],
}


def extract_schema_properties(schema):
    properties = schema["properties"]

    return {property["name"] for property in properties}


class WeaviateDataStore(DataStore):
    def handle_errors(self, results: Optional[List[dict]]) -> List[str]:
        if not self or not results:
            return []

        error_messages = []
        for result in results:
            if (
                "result" not in result
                or "errors" not in result["result"]
                or "error" not in result["result"]["errors"]
            ):
                continue
            for message in result["result"]["errors"]["error"]:
                error_messages.append(message["message"])
                logger.exception(message["message"])

        return error_messages

    def __init__(self):
        auth_credentials = self._build_auth_credentials()

        url = os.environ.get("WEAVIATE_URL", WEAVIATE_URL_DEFAULT)

        logger.debug(
            f"Connecting to weaviate instance at {url} with credential type {type(auth_credentials).__name__}"
        )
        self.client = Client(url, auth_client_secret=auth_credentials)
        self.client.batch.configure(
            batch_size=WEAVIATE_BATCH_SIZE,
            dynamic=WEAVIATE_BATCH_DYNAMIC,  # type: ignore
            callback=self.handle_errors,  # type: ignore
            timeout_retries=WEAVIATE_BATCH_TIMEOUT_RETRIES,
            num_workers=WEAVIATE_BATCH_NUM_WORKERS,
        )

        if self.client.schema.contains(SCHEMA):
            current_schema = self.client.schema.get(WEAVIATE_CLASS)
            current_schema_properties = extract_schema_properties(current_schema)

            logger.debug(
                f"Found index {WEAVIATE_CLASS} with properties {current_schema_properties}"
            )
            logger.debug("Will reuse this schema")
        else:
            new_schema_properties = extract_schema_properties(SCHEMA)
            logger.debug(
                f"Creating collection {WEAVIATE_CLASS} with properties {new_schema_properties}"
            )
            self.client.schema.create_class(SCHEMA)

    @staticmethod
    def _build_auth_credentials():
        url = os.environ.get("WEAVIATE_URL", WEAVIATE_URL_DEFAULT)

        if WeaviateDataStore._is_wcs_domain(url):
            api_key = os.environ.get("WEAVIATE_API_KEY")
            if api_key is not None:
                return weaviate.auth.AuthApiKey(api_key=api_key)
            else:
                raise ValueError("WEAVIATE_API_KEY environment variable is not set")
        else:
            return None

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        doc_ids = []

        with self.client.batch as batch:
            for doc_id, doc_chunks in chunks.items():
                logger.debug(f"Upserting {doc_id} with {len(doc_chunks)} chunks")
                for doc_chunk in doc_chunks:
                    # we generate a uuid regardless of the format of the document_id because
                    # weaviate needs a uuid to store each document chunk and
                    # a document chunk cannot share the same uuid
                    doc_uuid = generate_uuid5(doc_chunk, WEAVIATE_CLASS)
                    metadata = doc_chunk.metadata
                    doc_chunk_dict = doc_chunk.dict()
                    doc_chunk_dict.pop("metadata")
                    for key, value in metadata.dict().items():
                        doc_chunk_dict[key] = value
                    doc_chunk_dict["chunk_id"] = doc_chunk_dict.pop("id")
                    doc_chunk_dict["source"] = (
                        doc_chunk_dict.pop("source").value
                        if doc_chunk_dict["source"]
                        else None
                    )
                    embedding = doc_chunk_dict.pop("embedding")

                    batch.add_data_object(
                        uuid=doc_uuid,
                        data_object=doc_chunk_dict,
                        class_name=WEAVIATE_CLASS,
                        vector=embedding,
                    )

                doc_ids.append(doc_id)
            batch.flush()
        return doc_ids

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """

        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            logger.debug(f"Query: {query.query}")
            if not hasattr(query, "filter") or not query.filter:
                result = (
                    self.client.query.get(
                        WEAVIATE_CLASS,
                        [
                            "chunk_id",
                            "document_id",
                            "text",
                            "source",
                            "source_id",
                            "url",
                            "created_at",
                            "author",
                        ],
                    )
                    .with_hybrid(query=query.query, alpha=0.5, vector=query.embedding)
                    .with_limit(query.top_k)  # type: ignore
                    .with_additional(["score", "vector"])
                    .do()
                )
            else:
                filters_ = self.build_filters(query.filter)
                result = (
                    self.client.query.get(
                        WEAVIATE_CLASS,
                        [
                            "chunk_id",
                            "document_id",
                            "text",
                            "source",
                            "source_id",
                            "url",
                            "created_at",
                            "author",
                        ],
                    )
                    .with_hybrid(query=query.query, alpha=0.5, vector=query.embedding)
                    .with_where(filters_)
                    .with_limit(query.top_k)  # type: ignore
                    .with_additional(["score", "vector"])
                    .do()
                )

            query_results: List[DocumentChunkWithScore] = []
            response = result["data"]["Get"][WEAVIATE_CLASS]

            for resp in response:
                result = DocumentChunkWithScore(
                    id=resp["chunk_id"],
                    text=resp["text"],
                    # embedding=resp["_additional"]["vector"],
                    score=resp["_additional"]["score"],
                    metadata=DocumentChunkMetadata(
                        document_id=resp["document_id"] if resp["document_id"] else "",
                        source=Source(resp["source"]) if resp["source"] else None,
                        source_id=resp["source_id"],
                        url=resp["url"],
                        created_at=resp["created_at"],
                        author=resp["author"],
                    ),
                )
                query_results.append(result)
            return QueryResult(query=query.query, results=query_results)

        return await asyncio.gather(*[_single_query(query) for query in queries])

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        # TODO
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Returns whether the operation was successful.
        """
        if delete_all:
            logger.debug(f"Deleting all vectors in index {WEAVIATE_CLASS}")
            self.client.schema.delete_all()
            return True

        if ids:
            operands = [
                {"path": ["document_id"], "operator": "Equal", "valueString": id}
                for id in ids
            ]

            where_clause = {"operator": "Or", "operands": operands}

            logger.debug(f"Deleting vectors from index {WEAVIATE_CLASS} with ids {ids}")
            result = self.client.batch.delete_objects(
                class_name=WEAVIATE_CLASS, where=where_clause, output="verbose"
            )

            if not bool(result["results"]["successful"]):
                logger.debug(
                    f"Failed to delete the following objects: {result['results']['objects']}"
                )

        if filter:
            where_clause = self.build_filters(filter)

            logger.debug(
                f"Deleting vectors from index {WEAVIATE_CLASS} with filter {where_clause}"
            )
            result = self.client.batch.delete_objects(
                class_name=WEAVIATE_CLASS, where=where_clause
            )

            if not bool(result["results"]["successful"]):
                logger.debug(
                    f"Failed to delete the following objects: {result['results']['objects']}"
                )

        return True

    @staticmethod
    def build_filters(filter):
        if filter.source:
            filter.source = filter.source.value

        operands = []
        filter_conditions = {
            "source": {
                "operator": "Equal",
                "value": "query.filter.source.value",
                "value_key": "valueString",
            },
            "start_date": {"operator": "GreaterThanEqual", "value_key": "valueDate"},
            "end_date": {"operator": "LessThanEqual", "value_key": "valueDate"},
            "default": {"operator": "Equal", "value_key": "valueString"},
        }

        for attr, value in filter.__dict__.items():
            if value is not None:
                filter_condition = filter_conditions.get(
                    attr, filter_conditions["default"]
                )
                value_key = filter_condition["value_key"]

                operand = {
                    "path": [
                        attr
                        if not (attr == "start_date" or attr == "end_date")
                        else "created_at"
                    ],
                    "operator": filter_condition["operator"],
                    value_key: value,
                }

                operands.append(operand)

        return {"operator": "And", "operands": operands}

    @staticmethod
    def _is_valid_weaviate_id(candidate_id: str) -> bool:
        """
        Check if candidate_id is a valid UUID for weaviate's use

        Weaviate supports UUIDs of version 3, 4 and 5. This function checks if the candidate_id is a valid UUID of one of these versions.
        See https://weaviate.io/developers/weaviate/more-resources/faq#q-are-there-restrictions-on-uuid-formatting-do-i-have-to-adhere-to-any-standards
        for more information.
        """
        acceptable_version = [3, 4, 5]

        try:
            result = uuid.UUID(candidate_id)
            if result.version not in acceptable_version:
                return False
            else:
                return True
        except ValueError:
            return False

    @staticmethod
    def _is_wcs_domain(url: str) -> bool:
        """
        Check if the given URL ends with ".weaviate.network" or ".weaviate.network/".

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL ends with the specified strings, False otherwise.
        """
        pattern = r"\.(weaviate\.cloud|weaviate\.network)(/)?$"
        return bool(re.search(pattern, url))
