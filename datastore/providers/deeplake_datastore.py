import os
from typing import Any, Dict, List, Tuple, Optional
import deeplake
from tenacity import retry, wait_random_exponential, stop_after_attempt
import asyncio
from loguru import logger
import numpy as np

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

# Read environment variables for Deep Lake configuration
DEEPLAKE_PATH = os.environ.get("DEEPLAKE_PATH")
DEEPLAKE_API_KEY = os.environ.get("DEEPLAKE_API_KEY")

# Set the batch size for upserting vectors to Deep Lake
UPSERT_BATCH_SIZE = 100


def L2_search(
    query_embedding: np.ndarray, data_vectors: np.ndarray, k: int = 4
) -> Tuple[List, List]:
    """naive L2 search for nearest neighbors"""
    # Calculate the L2 distance between the query_vector and all data_vectors
    distances = np.linalg.norm(data_vectors - query_embedding, axis=1)

    # Sort the distances and return the indices of the k nearest vectors
    nearest_indices = np.argsort(distances)[:k]
    return nearest_indices.tolist(), distances[nearest_indices].tolist()


class DeepLakeDataStore(DataStore):
    def __init__(self, dataset_path: str = "./.deeplake/dataset", token: str = DEEPLAKE_API_KEY):

        self.dataset_path = DEEPLAKE_PATH or dataset_path
        self.token = DEEPLAKE_API_KEY or token

        """Initialize the Deep Lake DataStore with the dataset path and API key.
        
        Args:
            dataset_path (str, optional): The path to the dataset in Deep Lake. Defaults to DEEPLAKE_PATH.
            token (str, optional): The API key for Deep Lake. Defaults to DEEPLAKE_API_KEY.
        """
        if deeplake.exists(dataset_path, token=token):
            self.ds = deeplake.load(dataset_path, token=token)
            logger.warning(
                f"Deep Lake Dataset in {dataset_path} already exists, "
                f"loading from the storage"
            )
        else:
            self._create_dataset()

        self.ds.summary()

    def _create_dataset(self):
        """ Create an empty dataset in Deep Lake and defines tensors."""
        self.ds = deeplake.empty(
            self.dataset_path, token=self.token, overwrite=True)

        with self.ds:
            self.ds.create_tensor("ids", htype="text", create_id_tensor=False,
                                  create_sample_info_tensor=False, create_shape_tensor=False)
            self.ds.create_tensor("metadata", htype="json", create_id_tensor=False,
                                  create_sample_info_tensor=False, create_shape_tensor=False)
            self.ds.create_tensor("embedding", htype="generic", create_id_tensor=False,
                                  create_sample_info_tensor=False, create_shape_tensor=False)
            self.ds.create_tensor("created_at", htype="generic", create_id_tensor=False,
                                  create_sample_info_tensor=False, create_shape_tensor=False)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """Upsert chunks into the datastore.

        Args:
            chunks (Dict[str, List[DocumentChunk]]): A list of DocumentChunks to insert

        Raises:
            e: Error in upserting data.

        Returns:
            List[str]: The document_id's that were inserted.
        """
        docs = []
        doc_ids = []
        for doc_id, doc_chunks in chunks.items():

            logger.debug(f"Upserting {doc_id} with {len(doc_chunks)} chunks")
            for doc_chunk in doc_chunks:

                metadata = doc_chunk.metadata
                doc_chunk_dict = doc_chunk.dict()
                for key, value in metadata.dict().items():
                    doc_chunk_dict[key] = value

                doc_chunk_dict["chunk_id"] = doc_chunk_dict.pop("id")
                doc_chunk_dict["source"] = (
                    doc_chunk_dict.pop("source").value
                    if doc_chunk_dict["source"]
                    else None
                )
                tstamp = to_unix_timestamp(metadata.created_at)
                embedding = doc_chunk_dict.pop("embedding")
                docs.append((embedding, doc_chunk_dict,
                            doc_chunk_dict["chunk_id"], tstamp))

            doc_ids.append(doc_id)

        @deeplake.compute
        def ingest(sample_in: list, sample_out: list) -> None:
            s = {
                "embedding": np.array(sample_in[0]),
                "metadata": sample_in[1],
                "ids": sample_in[2],
                "created_at": sample_in[3],
            }
            sample_out.append(s)

        ingest().eval(list(docs), self.ds)
        self.ds.commit(allow_empty=True)

        return doc_ids

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """Query the QueryWithEmbedding against the Deep Lake datastore

        Search the embedding and its filter in the collection.

        Args:
            queries (List[QueryWithEmbedding]): The list of searches to perform.

        Returns:
            List[QueryResult]: Results for each search.
        """
        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            # Set the filter to expression that is valid for Deep Lake
            view = self.ds

            if query.filter != None:
                filter = self._get_filter(query.filter)
                view = self.ds.filter(filter)

            # Loads all embeddings into memory
            embeddings = view.embedding.numpy()

            if len(view) == 0:
                return QueryResult(
                    query=query.query,
                    results=[],
                )

            indices, scores = L2_search(
                query.embedding, embeddings, k=query.top_k)

            # Results that will hold our DocumentChunkWithScores
            results = []

            # Parse every result for our search
            for id, score in zip(indices, scores):  # type: ignore
                # Our metadata info, falls under DocumentChunkMetadata
                metadata = view.metadata[id].data()["value"]

                # If the source isn't valid, convert to None
                if metadata["source"] not in Source.__members__:
                    metadata["source"] = None

                # Text falls under the DocumentChunk
                text = metadata.pop("text")

                # Id falls under the DocumentChunk
                ids = view.ids[id].data()["value"]  # metadata.pop("id")

                chunk = DocumentChunkWithScore(
                    id=ids,
                    score=score,
                    text=text,
                    metadata=DocumentChunkMetadata(**metadata),
                )
                results.append(chunk)

            return QueryResult(query=query.query, results=results)

        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )
        return results

    def _get_filter(self, filter: DocumentMetadataFilter) -> Optional[str]:
        """Converts a DocumentMetdataFilter to the expression that Deep Lake takes.

        Args:
            filter (DocumentMetadataFilter): The Filter to convert to Deep Lake expression.

        Returns:
            Optional[str]: The filter if valid, otherwise None.
        """
        filter = filter.dict()

        def dp_filter(x):
            if 'start_date' in filter and filter['start_date'] is not None and x['created_at'].numpy() < to_unix_timestamp(filter['start_date']):
                return False

            if 'end_date' in filter and filter['end_date'] is not None and x['created_at'].numpy() > to_unix_timestamp(filter['end_date']):
                return False

            metadata = x['metadata'].data()["value"]

            if filter['source'] is not None and "source" in metadata and metadata["source"] != filter['source'].value:
                return False

            if any([metadata[k] != v for k, v in filter.items() if v is not None and v in x['metadata']]):
                return False

            return True

        return dp_filter

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """Delete the entities based either on the chunk_id of the vector,

        Args:
            ids (Optional[List[str]], optional): The document_ids to delete. Defaults to None.
            filter (Optional[DocumentMetadataFilter], optional): The filter to delete by. Defaults to None.
            delete_all (Optional[bool], optional): Whether to drop the collection and recreate it. Defaults to None.
        """
        if delete_all:
            self._create_dataset()
            return True

        view = None
        if ids:
            view = self.ds.filter(lambda x: x['metadata'].data()[
                                  'value']['document_id'] in ids)
            ids = list(view.sample_indices)

        if filter:
            if view is None:
                view = self.ds
            filter = self._get_filter(filter)
            view = view.filter(filter)
            ids = list(view.sample_indices)

        with self.ds:
            for id in sorted(ids)[::-1]:
                self.ds.pop(id)
            self.ds.commit(f'deleted {len(ids)} samples', allow_empty=True)

        return True
