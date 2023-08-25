"""
Chroma datastore support for the ChatGPT retrieval plugin.

Consult the Chroma docs and GitHub repo for more information:
- https://docs.trychroma.com/usage-guide?lang=py
- https://github.com/chroma-core/chroma
- https://www.trychroma.com/
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import chromadb

from datastore.datastore import DataStore
from models.models import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from services.chunks import get_document_chunks

CHROMA_IN_MEMORY = os.environ.get("CHROMA_IN_MEMORY", "True")
CHROMA_PERSISTENCE_DIR = os.environ.get("CHROMA_PERSISTENCE_DIR", "openai")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://127.0.0.1")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "openaiembeddings")


class ChromaDataStore(DataStore):
    def __init__(
        self,
        in_memory: bool = CHROMA_IN_MEMORY,  # type: ignore
        persistence_dir: Optional[str] = CHROMA_PERSISTENCE_DIR,
        collection_name: str = CHROMA_COLLECTION,
        host: str = CHROMA_HOST,
        port: str = CHROMA_PORT,
        client: Optional[chromadb.Client] = None,
    ):
        if client:
            self._client = client
        else:
            if in_memory:
                settings = (
                    chromadb.config.Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=persistence_dir,
                    )
                    if persistence_dir
                    else chromadb.config.Settings()
                )

                self._client = chromadb.Client(settings=settings)
            else:
                self._client = chromadb.Client(
                    settings=chromadb.config.Settings(
                        chroma_api_impl="rest",
                        chroma_server_host=host,
                        chroma_server_http_port=port,
                    )
                )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
        )

    async def upsert(
        self, documents: List[Document], chunk_token_size: Optional[int] = None
    ) -> List[str]:
        """
        Takes in a list of documents and inserts them into the database. If an id already exists, the document is updated.
        Return a list of document ids.
        """

        chunks = get_document_chunks(documents, chunk_token_size)

        # Chroma has a true upsert, so we don't need to delete first
        return await self._upsert(chunks)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """

        self._collection.upsert(
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
        if query_filter.source:
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
        stored_metadata = {}
        if metadata.source:
            stored_metadata["source"] = metadata.source.value
        if metadata.source_id:
            stored_metadata["source_id"] = metadata.source_id
        if metadata.url:
            stored_metadata["url"] = metadata.url
        if metadata.created_at:
            stored_metadata["created_at"] = int(
                datetime.fromisoformat(metadata.created_at).timestamp()
            )
        if metadata.author:
            stored_metadata["author"] = metadata.author
        if metadata.document_id:
            stored_metadata["document_id"] = metadata.document_id

        return stored_metadata

    def _process_metadata_from_storage(self, metadata: Dict) -> DocumentChunkMetadata:
        return DocumentChunkMetadata(
            source=Source(metadata["source"]) if "source" in metadata else None,
            source_id=metadata.get("source_id", None),
            url=metadata.get("url", None),
            created_at=datetime.fromtimestamp(metadata["created_at"]).isoformat()
            if "created_at" in metadata
            else None,
            author=metadata.get("author", None),
            document_id=metadata.get("document_id", None),
        )

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        results = [
            self._collection.query(
                query_embeddings=[query.embedding],
                include=["documents", "distances", "metadatas"],  # embeddings
                n_results=min(query.top_k, self._collection.count()),  # type: ignore
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
            # (embeddings,) = result["embeddings"]
            (documents,) = result["documents"]
            (metadatas,) = result["metadatas"]
            (distances,) = result["distances"]
            for id_, text, metadata, distance in zip(
                ids,
                documents,
                metadatas,
                distances,  # embeddings (https://github.com/openai/chatgpt-retrieval-plugin/pull/59#discussion_r1154985153)
            ):
                inner_results.append(
                    DocumentChunkWithScore(
                        id=id_,
                        text=text,
                        metadata=self._process_metadata_from_storage(metadata),
                        # embedding=embedding,
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
            self._collection.delete()
            return True

        if ids and len(ids) > 0:
            if len(ids) > 1:
                where_clause = {"$or": [{"document_id": id_} for id_ in ids]}
            else:
                (id_,) = ids
                where_clause = {"document_id": id_}

            if filter:
                where_clause = {
                    "$and": [self._where_from_query_filter(filter), where_clause]
                }
        elif filter:
            where_clause = self._where_from_query_filter(filter)

        self._collection.delete(where=where_clause)
        return True
