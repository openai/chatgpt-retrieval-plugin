"""
Chroma datastore support for the ChatGPT retrieval plugin.

Consult the Chroma docs and GitHub repo for more information:
- https://docs.trychroma.com/api-reference
- https://github.com/chroma-core/chroma
- https://www.trychroma.com/
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import chromadb
from chromadb.api.models import Collection

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

CHROMA_IN_MEMORY = os.environ.get("CHROMA_IN_MEMORY", "False")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://127.0.0.1")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "openaiembeddings")


class ChromaDataStore(DataStore):
    def __init__(
        self,
        client: Optional[chromadb.Client] = None,
    ):
        if client:
            self.client = client
        else:
            if CHROMA_IN_MEMORY == "True":
                self.client = chromadb.Client()
            else:
                self.client = chromadb.Client(
                    settings=chromadb.config.Settings(
                        chroma_server_host=CHROMA_HOST,
                        chroma_server_http_port=CHROMA_PORT,
                    )
                )
        self.collection = self.client.create_collection(
            name=CHROMA_COLLECTION, embedding_function=None
        )

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        self.collection.add(
            ids=[chunk.id for chunk_list in chunks.values() for chunk in chunk_list],
            embeddings=[
                chunk.embedding
                for chunk_list in chunks.values()
                for chunk in chunk_list
            ],
            documents=[
                chunk.text for chunk_list in chunks.values() for chunk in chunk_list
            ],
            metadatas=[
                self._process_metadata_for_storage(chunk.metadata)
                for chunk_list in chunks.values()
                for chunk in chunk_list
            ],
        )
        return list(chunks.keys())

    def _where_from_query_filter(self, query_filter: DocumentMetadataFilter) -> Dict:
        output = {
            k: v
            for (k, v) in query_filter.dict().items()
            if v is not None and k != "start_date" and k != "end_date" and k != "source"
        }
        output["source"] = query_filter.source.value
        if query_filter.start_date and query_filter.end_date:
            output["$and"] = [
                {
                    "created_at": {
                        "$gte": int(
                            datetime.fromisoformat(query_filter.start_date).timestamp()
                        )
                    }
                },
                {
                    "created_at": {
                        "$lte": int(
                            datetime.fromisoformat(query_filter.end_date).timestamp()
                        )
                    }
                },
            ]
        elif query_filter.start_date:
            output["created_at"] = {
                "$gte": int(datetime.fromisoformat(query_filter.start_date).timestamp())
            }
        elif query_filter.end_date:
            output["created_at"] = {
                "$lte": int(datetime.fromisoformat(query_filter.end_date).timestamp())
            }

        return output

    def _process_metadata_for_storage(self, metadata: DocumentChunkMetadata) -> Dict:
        return {
            "source": metadata.source.value,
            "source_id": metadata.source_id,
            "url": metadata.url,
            "created_at": int(datetime.fromisoformat(metadata.created_at).timestamp()),
            "author": metadata.author,
            "document_id": metadata.document_id,
        }

    def _process_metadata_from_storage(self, metadata: Dict) -> DocumentChunkMetadata:
        return DocumentChunkMetadata(
            source=Source(metadata["source"]),
            source_id=metadata["source_id"],
            url=metadata["url"],
            created_at=datetime.fromtimestamp(metadata["created_at"]).isoformat(),
            author=metadata["author"],
            document_id=metadata["document_id"],
        )

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        results = [
            self.collection.query(
                query_embeddings=[query.embedding],
                include=["documents", "distances", "metadatas", "embeddings"],
                n_results=min(query.top_k, self.collection.count()),
                where=(
                    self._where_from_query_filter(query.filter) if query.filter else {}
                ),
            )
            for query in queries
        ]

        output = []
        for query, result in zip(queries, results):
            inner_results = []
            (ids,) = result["ids"]
            (embeddings,) = result["embeddings"]
            (documents,) = result["documents"]
            (metadatas,) = result["metadatas"]
            (distances,) = result["distances"]
            for id_, embedding, text, metadata, distance in zip(
                ids, embeddings, documents, metadatas, distances
            ):
                inner_results.append(
                    DocumentChunkWithScore(
                        id=id_,
                        text=text,
                        metadata=self._process_metadata_from_storage(metadata),
                        embedding=embedding,
                        score=distance,
                    )
                )
            output.append(QueryResult(query=query.query, results=inner_results))

        return output

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Multiple parameters can be used at once.
        Returns whether the operation was successful.
        """
        if delete_all:
            self.collection.delete()
            return True

        self.collection.delete(
            ids=ids,
            where=(self._where_from_query_filter(filter) if filter else {}),
        )
        return True
