import os
from typing import Any, Dict, List, Optional

import dashvector
from dashvector import Client, Doc

from tenacity import retry, wait_random_exponential, stop_after_attempt
import asyncio
from loguru import logger

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

# Read environment variables for DashVector configuration
DASHVECTOR_API_KEY = os.environ.get("DASHVECTOR_API_KEY")
DASHVECTOR_COLLECTION = os.environ.get("DASHVECTOR_COLLECTION")
assert DASHVECTOR_API_KEY is not None
assert DASHVECTOR_COLLECTION is not None

# Set the batch size for vector upsert to DashVector
UPSERT_BATCH_SIZE = 100

# Set the dimension for embedding
VECTOR_DIMENSION = 1536


class DashVectorDataStore(DataStore):
    def __init__(self):
        # Init dashvector client
        client = Client(api_key=DASHVECTOR_API_KEY)
        self._client = client

        # Get the collection in DashVector
        collection = client.get(DASHVECTOR_COLLECTION)

        # Check if the collection exists in DashVector
        if collection:
            logger.info(f"Connected existed collection {DASHVECTOR_COLLECTION}.")
            self._collection = collection
        else:
            self._create_collection()

    @retry(wait=wait_random_exponential(min=1, max=20),
           stop=stop_after_attempt(3))
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict from document id to list of document chunks and inserts them into the collection.
        Return a list of document ids.
        """
        # Initialize a list of ids to return
        doc_ids: List[str] = []
        # Initialize a list of vectors to upsert
        docs = []
        # Loop through the dict items
        for doc_id, chunk_list in chunks.items():
            # Append the id to the ids list
            doc_ids.append(doc_id)
            logger.info(f"Upserting document_id: {doc_id}")
            for chunk in chunk_list:
                fields = self._get_dashvector_fields(chunk.metadata)
                # Add the text to the fields
                fields["text"] = chunk.text
                docs.append(
                    Doc(id=chunk.id, vector=chunk.embedding, fields=fields)
                )

        # Split the vectors list into batches of the specified size
        batches = [
            docs[i: i + UPSERT_BATCH_SIZE]
            for i in range(0, len(docs), UPSERT_BATCH_SIZE)
        ]

        # Upsert each batch to DashVector
        for batch in batches:
            logger.info(f"Upserting batch of size {len(batch)}")
            resp = self._collection.upsert(docs=batch)
            if resp:
                logger.info("Upserted batch successfully")
            else:
                raise Exception(f"Failed to upsert batch, error: {resp}")

        return doc_ids

    @retry(wait=wait_random_exponential(min=1, max=20),
           stop=stop_after_attempt(3))
    async def _query(
            self,
            queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """

        # Define a helper coroutine that performs a single query and returns a QueryResult
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            logger.debug(f"Query: {query.query}")

            # Convert the metadata filter object to a dict with dashvector filter expressions
            dashvector_filter = self._get_dashvector_filter(query.filter)

            resp = self._collection.query(vector=query.embedding,
                                          topk=query.top_k,
                                          filter=dashvector_filter)
            if not resp:
                raise Exception(f"Error querying in collection: {resp}")

            query_results: List[DocumentChunkWithScore] = []
            for doc in resp:
                score = doc.score
                metadata = doc.fields
                text = metadata.pop("text")

                # Create a document chunk with score object with the result data
                result = DocumentChunkWithScore(
                    id=doc.id,
                    score=score,
                    text=text,
                    metadata=metadata,
                )
                query_results.append(result)
            return QueryResult(query=query.query, results=query_results)

        # Use asyncio.gather to run multiple _single_query coroutines concurrently and collect their results
        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        return results

    @retry(wait=wait_random_exponential(min=1, max=20),
           stop=stop_after_attempt(3))
    async def delete(
            self,
            ids: Optional[List[str]] = None,
            filter: Optional[DocumentMetadataFilter] = None,
            delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything from the collection.
        """

        # Delete all vectors from the collection if delete_all is True
        if delete_all:
            logger.info(f"Deleting all vectors from collection")
            resp = self._collection.delete(delete_all=True)
            if not resp:
                raise Exception(
                    f"Error deleting all vectors, error: {resp.message}"
                )
            logger.info(f"Deleted all vectors successfully")
            return True

        # Delete vectors by filter
        if filter:
            # Query the docs by filter
            resp = self._collection.query(topk=1024, filter=self._get_dashvector_filter(filter))
            if not resp:
                raise Exception(
                    f"Error deleting vectors with filter, error: {resp.message}"
                )
            if ids is not None:
                ids += [doc.id for doc in resp]
            else :
                ids = [doc.id for doc in resp]

        # Delete vectors that match the document ids from the collection if the ids list is not empty
        if ids is not None and len(ids) > 0:
            logger.info(f"Deleting vectors with ids {ids}")
            resp = self._collection.delete(ids)
            if not resp:
                raise Exception(
                    f"Error deleting vectors with ids, error: {resp.message}"
                )
            logger.info(f"Deleted vectors with ids successfully")
        return True

    def _get_dashvector_filter(
            self, filter: Optional[DocumentMetadataFilter] = None
    ) -> Optional[str]:
        if filter is None:
            return None

        dashvector_filter = []
        for field, value in filter.dict().items():
            if value is not None:
                if field == "start_date":
                    dashvector_filter.append(f"created_at >= {to_unix_timestamp(value)}")
                elif field == "end_date":
                    dashvector_filter.append(f"created_at <= {to_unix_timestamp(value)}")
                else:
                    if isinstance(value, str):
                        dashvector_filter.append(f"{field} = '{value}'")
                    else:
                        dashvector_filter.append(f"{field} = {value}")

        return " and ".join(dashvector_filter)

    def _get_dashvector_fields(
            self, metadata: Optional[DocumentChunkMetadata] = None
    ) -> Dict[str, Any]:
        dashvector_fields = {}
        # For each field in the Metadata, check if it has a value and add it to the dashvector fields
        for field, value in metadata.dict().items():
            if value is not None:
                if field == "created_at":
                    dashvector_fields[field] = to_unix_timestamp(value)
                elif field == "source":
                    dashvector_fields[field] = value.name
                else:
                    dashvector_fields[field] = value
        return dashvector_fields

    def _delete_collection(self) -> None:
        resp = self._client.delete(DASHVECTOR_COLLECTION)
        if not resp:
            raise Exception(
                f"Error delete collection, error: {resp.message}"
            )

    def _create_collection(self) -> None:
        """
        Create dashvector collection for vector management.
        """

        # Get all fields in the metadata object in a list
        fields_schema = {
            field: str for field in DocumentChunkMetadata.__fields__.keys()
            if field != "created_at"
        }
        # used for compare created time
        fields_schema["created_at"] = int

        logger.info(
            f"Creating collection {DASHVECTOR_COLLECTION} with metadata config {fields_schema}."
        )

        # Create new collection
        resp = self._client.create(
            DASHVECTOR_COLLECTION,
            dimension=VECTOR_DIMENSION,
            fields_schema=fields_schema
        )
        if not resp:
            raise Exception(
                f"Fail to create collection {DASHVECTOR_COLLECTION}. "
                f"Error: {resp.message}"
            )

        # set self collection
        collection = self._client.get(DASHVECTOR_COLLECTION)
        if not collection:
            raise Exception(
                f"Fail to get collection {DASHVECTOR_COLLECTION}. "
                f"Error: {collection}"
            )
        self._collection = collection
        logger.info(
            f"Collection {DASHVECTOR_COLLECTION} created successfully.")