import os
from typing import Dict, List, Any, Optional

import elasticsearch
from elasticsearch import Elasticsearch, helpers
from loguru import logger

from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)
from services.date import to_unix_timestamp

ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")
ELASTICSEARCH_CLOUD_ID = os.environ.get("ELASTICSEARCH_CLOUD_ID")
ELASTICSEARCH_USERNAME = os.environ.get("ELASTICSEARCH_USERNAME")
ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD")
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY")

ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX")
ELASTICSEARCH_REPLICAS = int(os.environ.get("ELASTICSEARCH_REPLICAS", "1"))
ELASTICSEARCH_SHARDS = int(os.environ.get("ELASTICSEARCH_SHARDS", "1"))

VECTOR_SIZE = int(os.environ.get("EMBEDDING_DIMENSION", 256))

UPSERT_BATCH_SIZE = 100


class ElasticsearchDataStore(DataStore):
    def __init__(
        self,
        index_name: Optional[str] = None,
        vector_size: int = VECTOR_SIZE,
        similarity: str = "cosine",
        replicas: int = ELASTICSEARCH_REPLICAS,
        shards: int = ELASTICSEARCH_SHARDS,
        recreate_index: bool = True,
    ):
        """
        Args:
            index_name: Name of the index to be used
            vector_size: Size of the embedding stored in a collection
            similarity:
                Any of "cosine" / "l2_norm" / "dot_product".

        """
        assert similarity in [
            "cosine",
            "l2_norm",
            "dot_product",
        ], "Similarity must be one of 'cosine' / 'l2_norm' / 'dot_product'."
        assert replicas > 0, "Replicas must be greater than or equal to 0."
        assert shards > 0, "Shards must be greater than or equal to 0."

        self.client = connect_to_elasticsearch(
            ELASTICSEARCH_URL,
            ELASTICSEARCH_CLOUD_ID,
            ELASTICSEARCH_API_KEY,
            ELASTICSEARCH_USERNAME,
            ELASTICSEARCH_PASSWORD,
        )
        assert (
            index_name != "" or ELASTICSEARCH_INDEX != ""
        ), "Please provide an index name."
        self.index_name = index_name or ELASTICSEARCH_INDEX or ""

        replicas = replicas or ELASTICSEARCH_REPLICAS
        shards = shards or ELASTICSEARCH_SHARDS

        # Set up the collection so the documents might be inserted or queried
        self._set_up_index(vector_size, similarity, replicas, shards, recreate_index)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        actions = []
        for _, chunkList in chunks.items():
            for chunk in chunkList:
                actions = (
                    actions
                    + self._convert_document_chunk_to_es_document_operation(chunk)
                )

        self.client.bulk(operations=actions, index=self.index_name)
        return list(chunks.keys())

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        searches = self._convert_queries_to_msearch_query(queries)
        results = self.client.msearch(searches=searches)
        return [
            QueryResult(
                query=query.query,
                results=[
                    self._convert_hit_to_document_chunk_with_score(hit)
                    for hit in result["hits"]["hits"]
                ],
            )
            for query, result in zip(queries, results["responses"])
        ]

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
                logger.info(f"Deleting all vectors from index")
                self.client.delete_by_query(
                    index=self.index_name, query={"match_all": {}}
                )
                logger.info(f"Deleted all vectors successfully")
                return True
            except Exception as e:
                logger.error(f"Error deleting all vectors: {e}")
                raise e

        # Convert the metadata filter object to a dict with elasticsearch filter expressions
        es_filters = self._get_es_filters(filter)
        # Delete vectors that match the filter from the index if the filter is not empty
        if es_filters != {}:
            try:
                logger.info(f"Deleting vectors with filter {es_filters}")
                self.client.delete_by_query(index=self.index_name, query=es_filters)
                logger.info(f"Deleted vectors with filter successfully")
            except Exception as e:
                logger.error(f"Error deleting vectors with filter: {e}")
                raise e

        if ids:
            try:
                documents_to_delete = [doc_id for doc_id in ids]
                logger.info(f"Deleting {len(documents_to_delete)} documents")
                res = self.client.delete_by_query(
                    index=self.index_name,
                    query={"terms": {"metadata.document_id": documents_to_delete}},
                )
                logger.info(f"Deleted documents successfully")
            except Exception as e:
                logger.error(f"Error deleting documents: {e}")
                raise e

        return True

    def _get_es_filters(
        self, filter: Optional[DocumentMetadataFilter] = None
    ) -> Dict[str, Any]:
        if filter is None:
            return {}

        es_filters = {
            "bool": {
                "must": [],
            }
        }

        # For each field in the MetadataFilter, check if it has a value and add the corresponding pinecone filter expression
        # For start_date and end_date, uses the range query - gte and lte operators respectively
        # For other fields, uses the term query
        for field, value in filter.dict().items():
            if value is not None:
                if field == "start_date":
                    es_filters["bool"]["must"].append(
                        {"range": {"created_at": {"gte": to_unix_timestamp(value)}}}
                    )
                elif field == "end_date":
                    es_filters["bool"]["must"].append(
                        {"range": {"created_at": {"lte": to_unix_timestamp(value)}}}
                    )
                else:
                    es_filters["bool"]["must"].append(
                        {"term": {f"metadata.{field}": value}}
                    )

        return es_filters

    def _convert_document_chunk_to_es_document_operation(
        self, document_chunk: DocumentChunk
    ) -> List[Dict]:
        created_at = (
            to_unix_timestamp(document_chunk.metadata.created_at)
            if document_chunk.metadata.created_at is not None
            else None
        )

        action_and_metadata = {
            "index": {
                "_index": self.index_name,
                "_id": document_chunk.id,
            }
        }

        source = {
            "id": document_chunk.id,
            "text": document_chunk.text,
            "metadata": document_chunk.metadata.dict(),
            "created_at": created_at,
            "embedding": document_chunk.embedding,
        }

        return [action_and_metadata, source]

    def _convert_queries_to_msearch_query(self, queries: List[QueryWithEmbedding]):
        searches = []

        for query in queries:
            searches.append({"index": self.index_name})
            searches.append(
                {
                    "_source": True,
                    "knn": {
                        "field": "embedding",
                        "query_vector": query.embedding,
                        "k": query.top_k,
                        "num_candidates": query.top_k,
                    },
                    "size": query.top_k,
                }
            )

        return searches

    def _convert_hit_to_document_chunk_with_score(self, hit) -> DocumentChunkWithScore:
        return DocumentChunkWithScore(
            id=hit["_id"],
            text=hit["_source"]["text"],  # type: ignore
            metadata=hit["_source"]["metadata"],  # type: ignore
            embedding=hit["_source"]["embedding"],  # type: ignore
            score=hit["_score"],
        )

    def _set_up_index(
        self,
        vector_size: int,
        similarity: str,
        replicas: int,
        shards: int,
        recreate_index: bool,
    ) -> None:
        if recreate_index:
            self._recreate_index(similarity, vector_size, replicas, shards)

        try:
            index_mapping = self.client.indices.get_mapping(index=self.index_name)
            current_similarity = index_mapping[self.index_name]["mappings"]["properties"]["embedding"]["similarity"]  # type: ignore
            current_vector_size = index_mapping[self.index_name]["mappings"]["properties"]["embedding"]["dims"]  # type: ignore

            if current_similarity != similarity:
                raise ValueError(
                    f"Collection '{self.index_name}' already exists in Elasticsearch, "
                    f"but it is configured with a similarity '{current_similarity}'. "
                    f"If you want to use that collection, but with a different "
                    f"similarity, please set `recreate_index=True` argument."
                )

            if current_vector_size != vector_size:
                raise ValueError(
                    f"Collection '{self.index_name}' already exists in Elasticsearch, "
                    f"but it is configured with a vector size '{current_vector_size}'. "
                    f"If you want to use that collection, but with a different "
                    f"vector size, please set `recreate_index=True` argument."
                )
        except elasticsearch.exceptions.NotFoundError:
            self._recreate_index(similarity, vector_size, replicas, shards)

    def _recreate_index(
        self, similarity: str, vector_size: int, replicas: int, shards: int
    ) -> None:
        settings = {
            "index": {
                "number_of_shards": shards,
                "number_of_replicas": replicas,
                "refresh_interval": "1s",
            }
        }
        mappings = {
            "properties": {
                "embedding": {
                    "type": "dense_vector",
                    "dims": vector_size,
                    "index": True,
                    "similarity": similarity,
                }
            }
        }

        self.client.indices.delete(
            index=self.index_name, ignore_unavailable=True, allow_no_indices=True
        )
        self.client.indices.create(
            index=self.index_name, mappings=mappings, settings=settings
        )


def connect_to_elasticsearch(
    elasticsearch_url=None, cloud_id=None, api_key=None, username=None, password=None
):
    # Check if both elasticsearch_url and cloud_id are defined
    if elasticsearch_url and cloud_id:
        raise ValueError(
            "Both elasticsearch_url and cloud_id are defined. Please provide only one."
        )

    # Initialize connection parameters dictionary
    connection_params = {}

    # Define the connection based on the provided parameters
    if elasticsearch_url:
        connection_params["hosts"] = [elasticsearch_url]
    elif cloud_id:
        connection_params["cloud_id"] = cloud_id
    else:
        raise ValueError("Please provide either elasticsearch_url or cloud_id.")

    # Add authentication details based on the provided parameters
    if api_key:
        connection_params["api_key"] = api_key
    elif username and password:
        connection_params["basic_auth"] = (username, password)
    else:
        logger.warning(
            "No authentication details provided. Please consider using an api_key or username and password to secure your connection."
        )

    # Establish the Elasticsearch client connection
    es_client = Elasticsearch(**connection_params)
    try:
        es_client.info()
    except Exception as e:
        logger.error(f"Error connecting to Elasticsearch: {e}")
        raise e

    return es_client
