import asyncio
import os
import time
from typing import Optional, List, Dict, Any

import searchium
from datastore.datastore import DataStore
from models.models import (
    DocumentMetadataFilter,
    QueryWithEmbedding,
    QueryResult,
    DocumentChunk, DocumentChunkMetadata, DocumentChunkWithScore
)
from searchium.fvs.model import DatasetStatus
from services.date import to_unix_timestamp

# Read environment variables for Searchium configuration
# retrieve this env from searchium cloud platform
SEARCHIUM_INSTANCE_ID = os.environ.get("SEARCHIUM_INSTANCE_ID")
# The dataset size for training and loading should be reasonably close to the actual size.
# The actual dataset size cannot be smaller than this parameter.
# Alternatively, you can run the training process/load manually.
# The actual minimum size should be at least 4,001.
SEARCHIUM_DATASET_SIZE = os.environ.get("SEARCHIUM_DATASET_SIZE")
# retrieve from searchium cloud platform
SEARCHIUM_CLIENT_API_URL = os.environ.get("SEARCHIUM_CLIENT_API_URL")
# dataset uuid
SEARCHIUM_DATASET_ID = os.environ.get("SEARCHIUM_DATASET_ID")

assert SEARCHIUM_INSTANCE_ID is not None  # UUID
assert SEARCHIUM_DATASET_ID is not None  # UUID
assert SEARCHIUM_DATASET_SIZE is not None  # int
assert SEARCHIUM_CLIENT_API_URL is not None  # str

UPSERT_BATCH_SIZE = 100

searchium.init(SEARCHIUM_INSTANCE_ID, SEARCHIUM_CLIENT_API_URL)


class SearchiumDataStore(DataStore):
    # flow: create dataset -> upsert documents -> train dataset -> load dataset -> search
    def __init__(self):
        try:
            list_ds = searchium.get_datasets()
            list_ids = [ds.id for ds in list_ds]
            if SEARCHIUM_DATASET_ID not in list_ids:
                self.dataset_id = searchium.create_dataset(SEARCHIUM_DATASET_ID).datasetId
                self.d_size = 0
                self.d_train = True
            else:
                self.dataset_id = SEARCHIUM_DATASET_ID
                dataset = searchium.get_dataset(self.dataset_id)
                size_db = dataset.numOfRecords
                size_db = size_db if size_db is not None else 0
                self.d_train = True if (dataset.datasetStatus is None or size_db == 0 or size_db < int(
                    SEARCHIUM_DATASET_SIZE)) else False
                self.d_size = size_db
            self.lock = asyncio.Lock()
        except Exception as e:
            raise e

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        # Initialize a list of ids to return
        doc_ids: List[str] = []
        # Initialize a list of vectors to upsert
        vectors: List[dict] = []
        # Loop through the dict items
        for doc_id, chunk_list in chunks.items():
            # Append the id to the ids list
            doc_ids.append(doc_id)
            print(f"Upserting document_id {doc_id}")
            for chunk in chunk_list:
                # add global doc_id
                searchium_metadata = self._get_searchium_metadata(chunk.metadata)
                searchium_metadata["document_id"] = doc_id
                searchium_metadata["text"] = chunk.text
                searchium_metadata["chunk_id"] = chunk.id
                vectors.append({"document_id": chunk.id, "vector": chunk.embedding, "metadata": searchium_metadata})

        # Split the vectors list into batches of the specified size
        batches = [
            vectors[i: i + UPSERT_BATCH_SIZE]
            for i in range(0, len(vectors), UPSERT_BATCH_SIZE)
        ]
        # Upsert each batch to Searchium
        for batch in batches:
            try:
                print(f"Upserting batch of size {len(batch)}")
                searchium.add_chunk(dataset_id=self.dataset_id, list_documents=batch)
                self.d_size = searchium.get_dataset(self.dataset_id).numOfRecords
                print(f"Upserted batch successfully")

                if ((self.d_size + 10) >= int(SEARCHIUM_DATASET_SIZE)) and self.d_train:
                    await self.lock.acquire()
                    print("training of the dataset has started.")
                    searchium.train_dataset(self.dataset_id)
                    self.d_train = False

                    status = searchium.get_dataset_status(self.dataset_id).datasetStatus
                    while (status is DatasetStatus.TRAINING) or (status is DatasetStatus.PENDING):
                        status = searchium.get_dataset_status(self.dataset_id).datasetStatus
                        print(f"dataset status: {status} in progress, awaiting {status} completion.")
                        time.sleep(10)

                    print("dataset loading has started.")
                    searchium.load_dataset(self.dataset_id)
                    print("dataset loaded successfully.")
            except Exception as e:
                print(f"Error upserting batch: {e}")
                raise e
            finally:
                if self.lock.locked():
                    self.lock.release()
        return doc_ids

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        # TODO: Add support for filters.

        async def _single_query(query: QueryWithEmbedding) -> QueryResult:
            print(f"Query: {query.query}")
            try:
                response = searchium.search(self.dataset_id, [query.embedding], query.top_k)
                result = res = zip(response.distance[0], response.metadata[0])
            except Exception as e:
                print(f"Error querying index: {e}")
                raise e

            query_results: List[DocumentChunkWithScore] = []
            for distance_query, metadata_query in result:
                if metadata_query is None: continue
                meta_clean = (
                    {key: value for key, value in metadata_query.items() if key != "text"} if metadata_query else None)
                res_query = DocumentChunkWithScore(
                    id=metadata_query["chunk_id"],
                    score=distance_query,
                    text=metadata_query["text"] if metadata_query and "text" in metadata_query else None,
                    metadata=meta_clean
                )
                query_results.append(res_query)
            return QueryResult(query=query.query, results=query_results)

        results: List[QueryResult] = await asyncio.gather(
            *[_single_query(query) for query in queries]
        )

        return results

    async def delete(self, ids: Optional[List[str]] = None, filter: Optional[DocumentMetadataFilter] = None,
                     delete_all: Optional[bool] = None) -> bool:
        # TODO: Add support for filters.

        # delete all documents
        if delete_all:
            try:
                print(f"Deleting all vectors from index")
                searchium.delete_document(self.dataset_id, delete_all=True)
                print(f"Deleted all vectors successfully")
                self.d_train = True
                self.d_size = 0
                return True
            except Exception as e:
                print(f"Error deleting all vectors: {e}")
                raise e

        # delete by id's
        if ids is not None and len(ids) > 0:
            try:
                print(f"Deleting vectors with ids {ids}")
                searchium.delete_document(self.dataset_id, ids)
                print(f"Deleted vectors with ids successfully")
            except Exception as e:
                print(f"Error deleting vectors with ids: {e}")
                raise e
        return True

    def _get_searchium_metadata(self, metadata: Optional[DocumentChunkMetadata] = None) -> Dict[str, Any]:
        if metadata is None:
            return {}

        searchium_metadata = {}

        # For each field in the Metadata, check if it has a value and add it to the pinecone metadata dict
        # For fields that are dates, convert them to unix timestamps
        for field, value in metadata.dict().items():
            if value is not None:
                if field in ["created_at"]:
                    searchium_metadata[field] = to_unix_timestamp(value)
                else:
                    searchium_metadata[field] = value

        return searchium_metadata
