import os
from typing import Any, Dict, List, Optional
import typesense
import asyncio

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

# Read environment variables for Typesense configuration
TYPESENSE_API_KEY = os.environ.get("TYPESENSE_API_KEY")
TYPESENSE_HOST = os.environ.get("TYPESENSE_HOST")
TYPESENSE_PROTOCOL = os.environ.get("TYPESENSE_PROTOCOL")
TYPESENSE_PORT = os.environ.get("TYPESENSE_PORT")
TYPESENSE_COLLECTION_NAME = os.environ.get("TYPESENSE_COLLECTION_NAME")
assert TYPESENSE_API_KEY is not None
assert TYPESENSE_COLLECTION_NAME is not None
assert TYPESENSE_HOST is not None
assert TYPESENSE_PROTOCOL is not None
assert TYPESENSE_PORT is not None

# Initialize Typesense with the API key and environment

typesense_client = \
    typesense.Client({
        "nodes": [{"host": TYPESENSE_HOST, "port": TYPESENSE_PORT, "protocol": TYPESENSE_PROTOCOL}],
        "api_key": TYPESENSE_API_KEY,
        "connection_timeout_seconds": 60
    })

# Set the batch size for upserting vectors
UPSERT_BATCH_SIZE = 100


class TypesenseDataStore(DataStore):
    def __init__(self):
        existing_collections = map(lambda c: c['name'], typesense_client.collections.retrieve())

        # Check if the collection already exists in Typesense
        if TYPESENSE_COLLECTION_NAME not in existing_collections:
            self._create_typesense_collection()

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a dict from document id to list of document chunks and inserts them into the collection.
        Return a list of document ids.
        """
        # Initialize a list of ids to return
        doc_ids: List[str] = []
        # Initialize a list of documents to upsert
        documents = []
        # Loop through the dict items
        for doc_id, chunk_list in chunks.items():
            # Append the id to the ids list
            doc_ids.append(doc_id)
            print(f"Upserting document_id: {doc_id}")
            for chunk in chunk_list:
                # Create a vector tuple of (id, embedding, metadata)
                # Convert the metadata object to a dict with unix timestamps for dates
                typesense_metadata = self._get_typesense_metadata(chunk.metadata)
                # Add the text and document id to the metadata dict
                typesense_metadata["text"] = chunk.text
                typesense_metadata["document_id"] = doc_id
                document = {
                    'id': chunk.id,
                    'embedding': chunk.embedding,
                    'metadata': typesense_metadata
                }
                documents.append(document)

        # Split the documents list into batches of the specified size
        batches = [
            documents[i: i + UPSERT_BATCH_SIZE]
            for i in range(0, len(documents), UPSERT_BATCH_SIZE)
        ]
        # Upsert each batch to Typesense
        for batch in batches:
            try:
                print(f"Upserting batch of size {len(batch)}")
                typesense_client.collections[TYPESENSE_COLLECTION_NAME].documents.import_(batch)
                print(f"Upserted batch successfully")
            except Exception as e:
                print(f"Error upserting batch: {e}")
                raise e

        return doc_ids

    async def _query(
            self,
            queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """

        # Define a helper coroutine that performs a single query and returns a QueryResult
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            print(f"Query: {query.query}")

            # Convert the metadata filter object to a dict with Typesense filter expressions
            typesense_filter = self._get_typesense_filter(query.filter)

            try:
                # Query the collection with the query embedding, filter, and top_k
                search_params = {
                    "searches": [
                        {
                            "q": "*",
                            "collection": TYPESENSE_COLLECTION_NAME,
                            "vector_query": f"embedding:([{','.join(str(v) for v in query.embedding)}], k:{query.top_k})",
                            "filter_by": typesense_filter
                        }
                    ]
                }
                print(search_params)
                query_response = typesense_client.multi_search.perform(search_params, {})

                if query_response['results'][0].get('error', None) is not None:
                    raise Exception(query_response['results'][0]['error'])

            except Exception as e:
                print(f"Error querying collection: {e}")
                raise e

            query_results: List[DocumentChunkWithScore] = []
            # print(query_response)
            for result_hit in query_response['results'][0]['hits']:
                result = result_hit['document']
                score = result_hit['vector_distance']
                metadata = result['metadata']
                # Remove document id and text from metadata and store it in a new variable
                metadata_without_text = (
                    {key: value for key, value in metadata.items() if key != "text"}
                    if metadata
                    else None
                )

                # If the source is not a valid Source in the Source enum, set it to None
                if (
                        metadata_without_text
                        and "source" in metadata_without_text
                        and metadata_without_text["source"] not in Source.__members__
                ):
                    metadata_without_text["source"] = None

                # Create a document chunk with score object with the result data
                result = DocumentChunkWithScore(
                    id=result['id'],
                    score=score,
                    text=metadata["text"] if metadata and "text" in metadata else None,
                    metadata=metadata_without_text,
                )
                query_results.append(result)
            return QueryResult(query=query.query, results=query_results)

        # Use asyncio.gather to run multiple _single_query coroutines concurrently and collect their results
        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        return results

    async def delete(
            self,
            ids: Optional[List[str]] = None,
            filter: Optional[DocumentMetadataFilter] = None,
            delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything from the collection.
        """
        # Delete all vectors from the index if delete_all is True
        if delete_all:
            try:
                print(f"Deleting all documents from collection")
                self._create_typesense_collection(delete_if_exists=True)
                print(f"Deleted all documents from collection successfully")
                return True
            except Exception as e:
                print(f"Error deleting all vectors: {e}")
                raise e

        # Convert the metadata filter object to a dict with typesense filter expressions
        typesense_filter = self._get_typesense_filter(filter)
        # Delete vectors that match the filter from the index if the filter is not empty
        if typesense_filter != '':
            try:
                print(f"Deleting documents with filter {typesense_filter}")
                typesense_client.collections[TYPESENSE_COLLECTION_NAME].documents.delete({'filter_by': typesense_filter})
                print(f"Deleting documents with filter successfully")
            except Exception as e:
                print(f"Error deleting documents with filter: {e}")
                raise e

        # Delete documents that match the document ids from the index if the ids list is not empty
        if ids is not None and len(ids) > 0:
            try:
                print(f"Deleting documents with ids {ids}")
                typesense_filter = f"metadata.document_id:=[{','.join(ids)}]"
                typesense_client.collections[TYPESENSE_COLLECTION_NAME].documents.delete({'filter_by': typesense_filter})
                print(f"Deleted documents with ids successfully")
            except Exception as e:
                print(f"Error deleting documents with ids: {e}")
                raise e

        return True

    def _get_typesense_filter(
            self, filter: Optional[DocumentMetadataFilter] = None
    ) -> str:
        if filter is None:
            return ''

        typesense_filters = []

        # For each field in the MetadataFilter, check if it has a value and add the corresponding typesense filter expression
        # For start_date and end_date, uses the >= and <= operators respectively
        # For other fields, uses the := operator
        for field, value in filter.dict().items():
            if value is not None:
                if field == "start_date":
                    typesense_filters.append(f'metadata.created_at:>={to_unix_timestamp(value)}')
                elif field == "end_date":
                    typesense_filters.append(f'metadata.created_at:<={to_unix_timestamp(value)}')
                else:
                    typesense_filters.append(f'metadata.{field}:={value}')

        return ' && '.join(typesense_filters)

    def _get_typesense_metadata(
            self, metadata: Optional[DocumentChunkMetadata] = None
    ) -> Dict[str, Any]:
        if metadata is None:
            return {}

        typesense_metadata = {}

        # For each field in the Metadata, check if it has a value and add it to the typesense metadata dict
        # For fields that are dates, convert them to unix timestamps
        for field, value in metadata.dict().items():
            if value is not None:
                if field in ["created_at"]:
                    typesense_metadata[field] = to_unix_timestamp(value)
                else:
                    typesense_metadata[field] = value

        return typesense_metadata

    def _create_typesense_collection(self, delete_if_exists=False):
        if delete_if_exists:
            try:
                typesense_client.collections['wikipedia_articles'].delete()
            except Exception as e:
                pass

        # Get all fields in the metadata object in a list
        fields_to_index = list(DocumentChunkMetadata.__fields__.keys())

        # Create a new collection with the specified name, dimension, and metadata configuration
        try:
            print(
                f"Creating collection {TYPESENSE_COLLECTION_NAME} with metadata config {fields_to_index}"
            )

            # field_definitions = fields_to_index.map(lambda f: {'name': f, 'type': 'auto', 'optional': True})
            field_definitions = [
                {'name': 'embedding', 'type': 'float[]', 'num_dim': 1536, 'optional': True},
                {'name': 'metadata', 'type': 'object', 'optional': True},
                {'name': 'metadata.document_id', 'type': 'string', 'optional': True},
                {'name': 'metadata.source', 'type': 'string', 'optional': True},
                {'name': 'metadata.source_id', 'type': 'string', 'optional': True},
                {'name': 'metadata.author', 'type': 'string', 'optional': True},
                {'name': 'metadata.start_date', 'type': 'int64', 'optional': True},
                {'name': 'metadata.end_date', 'type': 'int64', 'optional': True},
                {'name': 'metadata.created_at', 'type': 'int64', 'optional': True},
                {'name': 'metadata.text', 'type': 'string', 'optional': True},
            ]

            schema = {
                "name": TYPESENSE_COLLECTION_NAME,
                "fields": field_definitions,
                "enable_nested_fields": True
            }
            typesense_client.collections.create(schema)

            print(f"Collection {TYPESENSE_COLLECTION_NAME} created successfully")
        except Exception as e:
            print(f"Error creating collection {TYPESENSE_COLLECTION_NAME}: {e}")
            raise e