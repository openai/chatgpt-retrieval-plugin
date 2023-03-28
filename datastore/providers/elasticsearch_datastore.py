import json
import os
import uuid
from typing import Dict, List, Optional

import elasticsearch
from elasticsearch import Elasticsearch, helpers

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
ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "document_chunks")
ELASTICSEARCH_REPLICAS = os.environ.get("ELASTICSEARCH_REPLICAS", 2)
ELASTICSEARCH_SHARDS = os.environ.get("ELASTICSEARCH_SHARDS", 2)


class ElasticsearchDataStore(DataStore):
    UUID_NAMESPACE = uuid.UUID("3896d314-1e95-4a3a-b45a-945f9f0b541d")

    def __init__(
        self,
        index_name: Optional[str] = None,
        vector_size: int = 1536,
        similarity: str = "cosine",
        replicas: int = 2,
        shards: int = 2,
        recreate_index: bool = False,
    ):
        """
        Args:
            index_name: Name of the index to be used
            vector_size: Size of the embedding stored in a collection
            similarity:
                Any of "cosine" / "l2_norm" / "dot_product".

        """
        assert (
            vector_size <= 1024
        ), "Vector size must be less than 1024 due to Lucene limitations: https://github.com/apache/lucene/issues/11507, https://github.com/apache/lucene/pull/874"
        assert similarity in [
            "cosine",
            "l2_norm",
            "dot_product",
        ], "Similarity must be one of 'cosine' / 'l2_norm' / 'dot_product'."
        assert replicas > 0, "Replicas must be greater than or equal to 0."
        assert shards > 0, "Shards must be greater than or equal to 0."

        self.client = Elasticsearch(ELASTICSEARCH_URL)
        self.index_name = index_name or ELASTICSEARCH_INDEX

        replicas = replicas or ELASTICSEARCH_REPLICAS
        shards = shards or ELASTICSEARCH_SHARDS

        # Set up the collection so the documents might be inserted or queried
        self._set_up_index(vector_size, similarity, replicas, shards, recreate_index)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        documents = [
            self._convert_document_chunk_to_document(chunk)
            for _, chunks in chunks.items()
            for chunk in chunks
        ]
        self.client.bulk(body="\n".join(documents), index=self.index_name)
        return list(chunks.keys())

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        query_body = self._convert_queries_to_msearch_query(queries)
        results = self.client.msearch(body=query_body, index=self.index_name)

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
        if ids is None and filter is None and delete_all is None:
            raise ValueError("Please provide one of the parameters: ids or delete_all.")
        if ids:
            documents_to_delete = [
                {
                    "_op_type": "delete",
                    "_index": self.index_name,
                    "_id": doc_id,
                }
                for doc_id in ids
            ]
            res = helpers.bulk(self.client, documents_to_delete)
            return res == (len(ids), [])

        if filter:
            raise NotImplementedError("Filtering is not implemented yet.")

        if delete_all:
            raise NotImplementedError("Deleting all is not implemented yet.")

    def _convert_document_chunk_to_document(self, document_chunk: DocumentChunk) -> str:
        created_at = (
            to_unix_timestamp(document_chunk.metadata.created_at)
            if document_chunk.metadata.created_at is not None
            else None
        )

        action_and_metadata = json.dumps(
            {
                "index": {
                    "_index": self.index_name,
                    "_id": self._create_document_chunk_id(document_chunk.id),
                }
            }
        )
        source = json.dumps(
            {
                "id": document_chunk.id,
                "text": document_chunk.text,
                "metadata": document_chunk.metadata.dict(),
                "created_at": created_at,
                "embedding": document_chunk.embedding,
            }
        )

        return "\n".join([action_and_metadata, source])

    def _create_document_chunk_id(self, external_id: Optional[str]) -> str:
        if external_id is None:
            return uuid.uuid4().hex
        return uuid.uuid5(self.UUID_NAMESPACE, external_id).hex

    def _convert_queries_to_msearch_query(
        self, queries: List[QueryWithEmbedding]
    ) -> str:
        request_body = ""

        for query in queries:
            payload = {
                "_source": True,
                "knn": {
                    "field": "embedding",
                    "query_vector": query.embedding,
                    "k": query.top_k,
                    "num_candidates": query.top_k,
                },
                "size": query.top_k,
            }

            header = {"index": self.index_name}
            request_body += f"{json.dumps(header)}\n"
            request_body += f"{json.dumps(payload)}\n"

        return request_body

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
        body = {
            "settings": {
                "index": {
                    "number_of_shards": shards,
                    "number_of_replicas": replicas,
                    "refresh_interval": "1s",
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "dense_vector",
                        "dims": vector_size,
                        "index": True,
                        "similarity": similarity,
                    }
                }
            },
        }
        self.client.indices.delete(index=self.index_name, ignore=[400, 404])
        self.client.indices.create(index=self.index_name, body=body, ignore=400)
