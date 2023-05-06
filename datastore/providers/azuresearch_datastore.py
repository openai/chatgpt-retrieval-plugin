import asyncio
import os
import re
import time
from typing import Dict, List, Optional, Union
from datastore.datastore import DataStore
from models.models import DocumentChunk, DocumentChunkMetadata, DocumentChunkWithScore, DocumentMetadataFilter, Query, QueryResult, QueryWithEmbedding
from azure.search.documents import SearchClient
from azure.search.documents.models import Vector
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

AZURESEARCH_SERVICE = os.environ.get("AZURESEARCH_SERVICE")
AZURESEARCH_INDEX = os.environ.get("AZURESEARCH_INDEX")
AZURESEARCH_API_KEY = os.environ.get("AZURESEARCH_API_KEY")
AZURESEARCH_SEMANTIC_CONFIG = os.environ.get("AZURESEARCH_SEMANTIC_CONFIG")
AZURESEARCH_URL_PREFIX = os.environ.get("AZURESEARCH_URL_PREFIX")
AZURESEARCH_DISABLE_HYBRID = os.environ.get("AZURESEARCH_DISABLE_HYBRID")
assert AZURESEARCH_SERVICE is not None
assert AZURESEARCH_INDEX is not None

# Allow overriding field names for Azure Search
FIELDS_ID = os.environ.get("AZURESEARCH_FIELDS_ID", "id")
FIELDS_TEXT = os.environ.get("AZURESEARCH_FIELDS_TEXT", "text")
FIELDS_EMBEDDING = os.environ.get("AZURESEARCH_FIELDS_TEXT", "embedding")
FIELDS_DOCUMENT_ID = os.environ.get("AZURESEARCH_FIELDS_DOCUMENT_ID", "document_id")
FIELDS_SOURCE = os.environ.get("AZURESEARCH_FIELDS_SOURCE", "source")
FIELDS_SOURCE_ID = os.environ.get("AZURESEARCH_FIELDS_SOURCE_ID", "source_id")
FIELDS_URL = os.environ.get("AZURESEARCH_FIELDS_URL", "url")
FIELDS_CREATED_AT = os.environ.get("AZURESEARCH_FIELDS_CREATED_AT", "created_at")
FIELDS_AUTHOR = os.environ.get("AZURESEARCH_FIELDS_AUTHOR", "author")

# Assume we're using OpenAI's ada-002 embedding model that uses a vector size of 1536
EMBEDDING_DIMENSIONS = 1536

MAX_UPLOAD_BATCH_SIZE = 1000
MAX_DELETE_BATCH_SIZE = 1000

class AzureSearchDataStore(DataStore):
    def __init__(self):
        credential = AzureSearchDataStore._create_credentials()

        self.client = SearchClient(
            endpoint=f"https://{AZURESEARCH_SERVICE}.search.windows.net",
            index_name=AZURESEARCH_INDEX,
            credential=credential
        )

        mgmt_client = SearchIndexClient(
            endpoint=f"https://{AZURESEARCH_SERVICE}.search.windows.net",
            credential=credential
        )
        if AZURESEARCH_INDEX not in [index.name for index in mgmt_client.list_indexes()]:
            self._create_index(mgmt_client)
        else:
            print(f"Using existing index {AZURESEARCH_INDEX} in service {AZURESEARCH_SERVICE}")
    
    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        azdocuments: List[Dict] = []

        def upload():
            r = self.client.upload_documents(documents=azdocuments)
            count = sum(1 for rr in r if rr.succeeded)
            print(f"Upserted {count} chunks out of {len(azdocuments)}")
            if count < len(azdocuments):
                raise Exception(f"Failed to upload {len(azdocuments) - count} chunks")

        ids = []
        for document_id, document_chunks in chunks.items():
            ids.append(document_id)
            for chunk in document_chunks:
                azdocuments.append({
                    FIELDS_ID: chunk.id,
                    FIELDS_TEXT: chunk.text,
                    FIELDS_EMBEDDING: chunk.embedding,
                    FIELDS_DOCUMENT_ID: document_id,
                    FIELDS_SOURCE: chunk.metadata.source,
                    FIELDS_SOURCE_ID: chunk.metadata.source_id,
                    FIELDS_URL: chunk.metadata.url,
                    FIELDS_CREATED_AT: chunk.metadata.created_at,
                    FIELDS_AUTHOR: chunk.metadata.author,
                })
            
                if len(azdocuments) >= MAX_UPLOAD_BATCH_SIZE:
                    upload()
                    azdocuments = []

        if len(azdocuments) > 0:
            upload()

        return ids

    async def delete(self, ids: Optional[List[str]] = None, filter: Optional[DocumentMetadataFilter] = None, delete_all: Optional[bool] = None) -> bool:
        filter = None if delete_all else self._translate_filter(filter)
        if delete_all or filter is not None:
            deleted = set()
            while True:
                search_result = self.client.search(None, filter=filter, top=MAX_DELETE_BATCH_SIZE, include_total_count=True, select=FIELDS_ID)
                if search_result.get_count() == 0:
                    break
                documents = [{ FIELDS_ID: d[FIELDS_ID] } for d in search_result if d[FIELDS_ID] not in deleted]
                if len(documents) > 0:
                    print(f"Deleting {len(documents)} chunks " + ("using a filter" if filter is not None else "using delete_all"))
                    del_result = self.client.delete_documents(documents=documents)
                    if not all([rr.succeeded for rr in del_result]):
                        raise Exception("Failed to delete documents")
                    deleted.update([d[FIELDS_ID] for d in documents])
                else:
                    # All repeats, delay a bit to let the index refresh and try again
                    time.sleep(0.25)
        
        if ids is not None and len(ids) > 0:
            for id in ids:
                print(f"Deleting chunks for document id {id}")
                await self.delete(filter=DocumentMetadataFilter(document_id=id))

        return True

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        return await asyncio.gather(*(self._single_query(query) for query in queries))
    
    async def _single_query(self, query: QueryWithEmbedding) -> QueryResult:
        """
        Takes in a single query and filters and returns a query result with matching document chunks and scores.
        """
        filter = self._translate_filter(query.filter) if query.filter is not None else None
        print(f"Querying with query: {query.query}, top: {query.top_k}, filter: {filter}")
        try:
            k = query.top_k if filter is None else query.top_k * 2
            q = query.query if not AZURESEARCH_DISABLE_HYBRID else None
            r = self.client.search(q, filter=filter, top=query.top_k, vector=Vector(value=query.embedding, k=k, fields=FIELDS_EMBEDDING))
            results: List[DocumentChunkWithScore] = []
            for hit in r:
                results.append(DocumentChunkWithScore(
                    id=hit[FIELDS_ID],
                    text=hit[FIELDS_TEXT],
                    metadata=DocumentChunkMetadata(
                        document_id=hit.get(FIELDS_DOCUMENT_ID) if FIELDS_DOCUMENT_ID != "-" else None,
                        source=hit.get(FIELDS_SOURCE) if FIELDS_SOURCE != "-" else None,
                        source_id=hit.get(FIELDS_SOURCE_ID) if FIELDS_SOURCE_ID != "-" else None,
                        url=hit.get(FIELDS_URL) if FIELDS_URL != "-" else ((AZURESEARCH_URL_PREFIX + hit.get(FIELDS_SOURCE_ID)) if AZURESEARCH_URL_PREFIX != None else None),
                        created_at=hit.get(FIELDS_CREATED_AT) if FIELDS_CREATED_AT != "-" else None,
                        author=hit.get(FIELDS_AUTHOR) if FIELDS_AUTHOR != "-" else None
                    ),
                    score=hit["@search.score"]
                ))
                
            return QueryResult(query=query.query, results=results)
        except Exception as e:
            raise Exception(f"Error querying the index: {e}")

    @staticmethod    
    def _translate_filter(filter: DocumentMetadataFilter) -> str:
        """
        Translates a DocumentMetadataFilter into an Azure Search filter string
        """
        if filter is None:
            return None        
        
        escape = lambda s: s.replace("'", "''")

        # regex to validate dates are in OData format
        date_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

        filter_list = []
        if filter.document_id is not None:
            filter_list.append(f"{FIELDS_DOCUMENT_ID} eq '{escape(filter.document_id)}'")
        if filter.source is not None:
            filter_list.append(f"{FIELDS_SOURCE} eq '{escape(filter.source)}'")
        if filter.source_id is not None:
            filter_list.append(f"{FIELDS_SOURCE_ID} eq '{escape(filter.source_id)}'")
        if filter.author is not None:
            filter_list.append(f"{FIELDS_AUTHOR} eq '{escape(filter.author)}'")
        if filter.start_date is not None:
            if not date_re.match(filter.start_date):
                raise ValueError(f"start_date must be in OData format, got {filter.start_date}")
            filter_list.append(f"{FIELDS_CREATED_AT} ge {filter.start_date}")
        if filter.end_date is not None:
            if not date_re.match(filter.end_date):
                raise ValueError(f"end_date must be in OData format, got {filter.end_date}")
            filter_list.append(f"{FIELDS_CREATED_AT} le {filter.end_date}")
        return " and ".join(filter_list) if len(filter_list) > 0 else None
    
    def _create_index(self, mgmt_client: SearchIndexClient):
        """
        Creates an Azure Cognitive Search index, including a semantic search configuration if a name is specified for it
        """
        print(
            f"Creating index {AZURESEARCH_INDEX} in service {AZURESEARCH_SERVICE}" +
            (f" with semantic search configuration {AZURESEARCH_SEMANTIC_CONFIG}" if AZURESEARCH_SEMANTIC_CONFIG is not None else "")
        )
        mgmt_client.create_index(
            SearchIndex(
                name=AZURESEARCH_INDEX,
                fields=[
                    SimpleField(name=FIELDS_ID, type=SearchFieldDataType.String, key=True),
                    SearchableField(name=FIELDS_TEXT, type=SearchFieldDataType.String, analyzer_name="en.Microsoft"),
                    SearchField(name=FIELDS_EMBEDDING, type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                                hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
                                dimensions=EMBEDDING_DIMENSIONS, vector_search_configuration="default"),
                    SimpleField(name=FIELDS_DOCUMENT_ID, type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name=FIELDS_SOURCE, type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name=FIELDS_SOURCE_ID, type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name=FIELDS_URL, type=SearchFieldDataType.String),
                    SimpleField(name=FIELDS_CREATED_AT, type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                    SimpleField(name=FIELDS_AUTHOR, type=SearchFieldDataType.String, filterable=True, sortable=True)
                ],
                semantic_settings=None if AZURESEARCH_SEMANTIC_CONFIG is None else SemanticSettings(
                    configurations=[SemanticConfiguration(
                        name=AZURESEARCH_SEMANTIC_CONFIG,
                        prioritized_fields=PrioritizedFields(
                            title_field=None, prioritized_content_fields=[SemanticField(field_name=FIELDS_TEXT)]
                        )
                    )]
                ),
                vector_search=VectorSearch(
                    algorithm_configurations=[
                        VectorSearchAlgorithmConfiguration(
                            name="default",
                            kind="hnsw",
                            # Could change to dotproduct for OpenAI's embeddings since they normalize vectors to unit length
                            hnsw_parameters=HnswParameters(metric="cosine") 
                        )
                    ]
                )
            )
        )

    @staticmethod
    def _create_credentials() -> Union[AzureKeyCredential, DefaultAzureCredential]:
        if AZURESEARCH_API_KEY is None:
            print("Using DefaultAzureCredential for Azure Search, make sure local identity or managed identity are set up appropriately")
            credential = DefaultAzureCredential()
        else:
            print("Using an API key to authenticate with Azure Search")
            credential = AzureKeyCredential(AZURESEARCH_API_KEY)
        return credential
