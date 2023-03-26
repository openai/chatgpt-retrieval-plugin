"""
Chroma datastore support for the ChatGPT retrieval plugin.

Consult the Chroma docs and GitHub repo for more information:
- https://docs.trychroma.com/api-reference
- https://github.com/chroma-core/chroma
- https://www.trychroma.com/
"""

import os
from typing import Dict, List, Optional

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from models.models import (
    DocumentChunk,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
)

CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://127.0.0.1")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "OpenAIEmbeddings")


class ChromaDataStore(DataStore):
    def __init__(self):
        embedding_function = OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.client = chromadb.Client(host=CHROMA_HOST, port=CHROMA_PORT)

        # TODO(csvoss): embedding_function here is not actually used?, since the
        # parent DataStore class already embeds the documents and passes
        # QueryWithEmbedding objects to _query. Determine whether this might
        # result in duplicate calls to the embeddings API?
        self.collection = self.client.create_collection(
            name=CHROMA_COLLECTION, embedding_function=embedding_function
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
                chunk.metadata.dict()
                for chunk_list in chunks.values()
                for chunk in chunk_list
            ],
        )

    def _where_from_query_filter(self, query_filter: DocumentMetadataFilter) -> Dict:
        output = {
            k: v
            for (k, v) in query_filter.dict().items()
            if v is not None and k != "start_date" and k != "end_date"
        }
        if query_filter.start_date:
            output["created_at"] = {"$gte": query_filter.start_date}
        if query_filter.end_date:
            if "created_at" in output:
                output["created_at"]["$lte"] = query_filter.end_date
            else:
                output["created_at"] = {"$lte": query_filter.end_date}

        return output

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        results = [
            self.collection.query(
                # TODO(csvoss): should this be query_embeddings instead?
                query_texts=[query.query],
                include=["documents", "distances"],
                n_results=query.top_k,
                where=(
                    self._where_from_query_filter(query.filter) if query.filter else {}
                ),
            )
            for query in queries
        ]

        return [
            QueryResult(
                query=query.query,
                results=[
                    DocumentChunkWithScore(
                        id=id_,
                        text=text,
                        metadata=metadata,
                        embedding=query.embedding,
                        score=distance,
                    )
                    for id_, text, metadata, distance in zip(
                        result["documents"], result["metadatas"], result["distances"]
                    )
                ],
            )
            for (query, result) in zip(queries, results)
        ]

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
