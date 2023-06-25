import asyncio
import copy
import os

import tair
from tair.tairvector import DistanceMetric
from tair.tairvector import VectorType
from services.date import to_unix_timestamp
from datastore.datastore import DataStore
from typing import Dict, List, Optional, Union
from models.models import (
    DocumentChunk,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding, DocumentChunkMetadata,
)

TAIR_HOST = os.environ.get("TAIR_HOST", "localhost")
TAIR_PORT = int(os.environ.get("TAIR_PORT", 6379))
TAIR_USERNAME = os.environ.get("TAIR_USERNAME")
TAIR_PASSWORD = os.environ.get("TAIR_PASSWORD")
TAIR_INDEX_NAME = os.environ.get("TAIR_INDEX_NAME", "index")
TAIR_INDEX_TYPE = os.environ.get("TAIR_INDEX_TYPE", "FLAT")
TAIR_DISTANCE_METRIC = os.environ.get("TAIR_DISTANCE_METRIC", DistanceMetric.InnerProduct)
assert TAIR_INDEX_TYPE in ("FLAT", "HNSW")
assert TAIR_USERNAME is not None
assert TAIR_PASSWORD is not None
VECTOR_DIMENSION = 1536


class TairDataStore(DataStore):
    def __init__(self):
        try:
            self.client = tair.Tair(host=TAIR_HOST, port=TAIR_PORT, username=TAIR_USERNAME, password=TAIR_PASSWORD)
        except Exception as e:
            raise e

        ret = self.client.tvs_get_index(TAIR_INDEX_NAME)
        if ret is None:
            self.client.tvs_create_index(TAIR_INDEX_NAME, VECTOR_DIMENSION, distance_type=TAIR_DISTANCE_METRIC,
                                         index_type=TAIR_INDEX_TYPE)

    @staticmethod
    def _tair_key(document_id: str, chunk_id: str) -> str:
        return f"doc:{document_id}:chunk:{chunk_id}"

    def _find_keys(self, pattern: str):
        return self.client.tvs_scan(TAIR_INDEX_NAME, pattern=pattern)

    def _tair_delete(self, keys: List[str]):
        for key in keys:
            self.client.tvs_del(TAIR_INDEX_NAME, key)

    def _del_index(self):
        self.client.tvs_del_index(TAIR_INDEX_NAME)

    def _get_attrs(self, chunk: DocumentChunk) -> dict:
        # Convert chunk -> dict
        attrs = copy.deepcopy(chunk.__dict__)
        attrs["chunk_id"] = attrs.pop("id")

        metadata = chunk.metadata.__dict__
        if metadata:
            for field, value in metadata.items():
                if value:
                    if field == "created_at":
                        attrs[field] = to_unix_timestamp(value)
                    else:
                        attrs[field] = value
                else:
                    attrs[field] = ""
        attrs.pop("metadata")
        attrs.pop("embedding")
        return attrs

    @staticmethod
    def _get_vector(chunk: DocumentChunk) -> Union[VectorType, str]:
        return chunk.embedding

    def _get_filter(self, query: QueryWithEmbedding) -> str:
        filter_str: str = ""

        def _typ_to_str(field, value) -> str:  # type: ignore
            if field == "start_date":
                num = to_unix_timestamp(value)
                return f"created_at>={num}"
            elif field == "end_date":
                num = to_unix_timestamp(value)
                return f"created_at<={num}"
            else:
                return f"{field}==\"{value}\""

        # Build filter
        if query.filter:
            for field, value in query.filter.__dict__.items():
                if not value:
                    continue
                filter_str += _typ_to_str(field, value)
                filter_str += "&&"

        filter_str = filter_str.strip().strip("&&")
        return filter_str

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        doc_ids: List[str] = []

        # Loop through the dict items
        for doc_id, chunk_list in chunks.items():
            # Append the id to the ids list
            doc_ids.append(doc_id)

            # Write all chunks associated with a document
            async def _write(chunk: DocumentChunk):
                key = self._tair_key(doc_id, chunk.id)  # type: ignore
                attrs = self._get_attrs(chunk)
                vec = self._get_vector(chunk)
                self.client.tvs_hset(TAIR_INDEX_NAME, key, vector=vec, **attrs)

            # Concurrently gather writes
            await asyncio.gather(*[_write(chunk) for i, chunk in enumerate(chunk_list)])
        return doc_ids

    async def _query(
            self,
            queries: List[QueryWithEmbedding]
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and
        returns a list of query results with matching document chunks and scores.
        """
        results: List[QueryResult] = []

        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            filter_str = self._get_filter(query)
            return self.client.tvs_knnsearch(TAIR_INDEX_NAME, query.top_k, query.embedding,
                                             filter_str=filter_str)

        query_responses = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        # Iterate through responses and construct results
        for query, query_response in zip(queries, query_responses):
            query_results: List[DocumentChunkWithScore] = []
            for key, score in query_response:
                attrs = self.client.tvs_hgetall(TAIR_INDEX_NAME, key)
                meta_data = DocumentChunkMetadata(
                    document_id=attrs["document_id"],
                    source=attrs["source"],
                    source_id=attrs["source_id"],
                    url=attrs["url"],
                    created_at=attrs["created_at"],
                    author=attrs["author"]
                )

                result = DocumentChunkWithScore(
                    id=attrs["document_id"],
                    score=score,
                    text=attrs["text"],
                    metadata=meta_data
                )
                query_results.append(result)
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
        # Delete all vectors from the index if delete_all is True
        if delete_all:
            try:
                self._del_index()
                return True
            except Exception as e:
                raise e

        # Delete by filter or ids
        document_ids = set()
        if filter and filter.document_id:
            document_ids.add(filter.document_id)
        if ids:
            for document_id in ids:
                document_ids.add(document_id)
        try:
            keys = []
            for document_id in document_ids:
                for k in (self._find_keys(f"doc:{document_id}:*")).iter():
                    keys.append(k)

            if len(keys) > 0:
                self._tair_delete(keys)
        except Exception as e:
            raise e

        return True
