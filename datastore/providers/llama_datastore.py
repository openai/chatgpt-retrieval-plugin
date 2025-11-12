import json
import os
from typing import Dict, List, Optional, Type
from loguru import logger
from datastore.datastore import DataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    Query,
    QueryResult,
    QueryWithEmbedding,
)

from llama_index.indices.base import BaseGPTIndex
from llama_index.indices.vector_store.base import GPTVectorStoreIndex
from llama_index.indices.query.schema import QueryBundle
from llama_index.response.schema import Response
from llama_index.data_structs.node_v2 import Node, DocumentRelationship, NodeWithScore
from llama_index.indices.registry import INDEX_STRUCT_TYPE_TO_INDEX_CLASS
from llama_index.data_structs.struct_type import IndexStructType
from llama_index.indices.response.builder import ResponseMode

INDEX_STRUCT_TYPE_STR = os.environ.get(
    "LLAMA_INDEX_TYPE", IndexStructType.SIMPLE_DICT.value
)
INDEX_JSON_PATH = os.environ.get("LLAMA_INDEX_JSON_PATH", None)
QUERY_KWARGS_JSON_PATH = os.environ.get("LLAMA_QUERY_KWARGS_JSON_PATH", None)
RESPONSE_MODE = os.environ.get("LLAMA_RESPONSE_MODE", ResponseMode.NO_TEXT.value)

EXTERNAL_VECTOR_STORE_INDEX_STRUCT_TYPES = [
    IndexStructType.DICT,
    IndexStructType.WEAVIATE,
    IndexStructType.PINECONE,
    IndexStructType.QDRANT,
    IndexStructType.CHROMA,
    IndexStructType.VECTOR_STORE,
]


def _create_or_load_index(
    index_type_str: Optional[str] = None,
    index_json_path: Optional[str] = None,
    index_type_to_index_cls: Optional[dict[str, Type[BaseGPTIndex]]] = None,
) -> BaseGPTIndex:
    """Create or load index from json path."""
    index_json_path = index_json_path or INDEX_JSON_PATH
    index_type_to_index_cls = (
        index_type_to_index_cls or INDEX_STRUCT_TYPE_TO_INDEX_CLASS
    )
    index_type_str = index_type_str or INDEX_STRUCT_TYPE_STR
    index_type = IndexStructType(index_type_str)

    if index_type not in index_type_to_index_cls:
        raise ValueError(f"Unknown index type: {index_type}")

    if index_type in EXTERNAL_VECTOR_STORE_INDEX_STRUCT_TYPES:
        raise ValueError("Please use vector store directly.")

    index_cls = index_type_to_index_cls[index_type]
    if index_json_path is None:
        return index_cls(nodes=[])  # Create empty index
    else:
        return index_cls.load_from_disk(index_json_path)  # Load index from disk


def _create_or_load_query_kwargs(
    query_kwargs_json_path: Optional[str] = None,
) -> Optional[dict]:
    """Create or load query kwargs from json path."""
    query_kwargs_json_path = query_kwargs_json_path or QUERY_KWARGS_JSON_PATH
    query_kargs: Optional[dict] = None
    if query_kwargs_json_path is not None:
        with open(INDEX_JSON_PATH, "r") as f:
            query_kargs = json.load(f)
    return query_kargs


def _doc_chunk_to_node(doc_chunk: DocumentChunk, source_doc_id: str) -> Node:
    """Convert document chunk to Node"""
    return Node(
        doc_id=doc_chunk.id,
        text=doc_chunk.text,
        embedding=doc_chunk.embedding,
        extra_info=doc_chunk.metadata.dict(),
        relationships={DocumentRelationship.SOURCE: source_doc_id},
    )


def _query_with_embedding_to_query_bundle(query: QueryWithEmbedding) -> QueryBundle:
    return QueryBundle(
        query_str=query.query,
        embedding=query.embedding,
    )


def _source_node_to_doc_chunk_with_score(
    node_with_score: NodeWithScore,
) -> DocumentChunkWithScore:
    node = node_with_score.node
    if node.extra_info is not None:
        metadata = DocumentChunkMetadata(**node.extra_info)
    else:
        metadata = DocumentChunkMetadata()

    return DocumentChunkWithScore(
        id=node.doc_id,
        text=node.text,
        score=node_with_score.score if node_with_score.score is not None else 1.0,
        metadata=metadata,
    )


def _response_to_query_result(
    response: Response, query: QueryWithEmbedding
) -> QueryResult:
    results = [
        _source_node_to_doc_chunk_with_score(node) for node in response.source_nodes
    ]
    return QueryResult(
        query=query.query,
        results=results,
    )


class LlamaDataStore(DataStore):
    def __init__(
        self, index: Optional[BaseGPTIndex] = None, query_kwargs: Optional[dict] = None
    ):
        self._index = index or _create_or_load_index()
        self._query_kwargs = query_kwargs or _create_or_load_query_kwargs()

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        doc_ids = []
        for doc_id, doc_chunks in chunks.items():
            logger.debug(f"Upserting {doc_id} with {len(doc_chunks)} chunks")

            nodes = [
                _doc_chunk_to_node(doc_chunk=doc_chunk, source_doc_id=doc_id)
                for doc_chunk in doc_chunks
            ]

            self._index.insert_nodes(nodes)
            doc_ids.append(doc_id)
        return doc_ids

    async def _query(
        self,
        queries: List[QueryWithEmbedding],
    ) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and
        returns a list of query results with matching document chunks and scores.
        """
        query_result_all = []
        for query in queries:
            if query.filter is not None:
                logger.warning("Filters are not supported yet, ignoring for now.")

            query_bundle = _query_with_embedding_to_query_bundle(query)

            # Setup query kwargs
            if self._query_kwargs is not None:
                query_kwargs = self._query_kwargs
            else:
                query_kwargs = {}
            # TODO: support top_k for other indices
            if isinstance(self._index, GPTVectorStoreIndex):
                query_kwargs["similarity_top_k"] = query.top_k

            response = await self._index.aquery(
                query_bundle, response_mode=RESPONSE_MODE, **query_kwargs
            )

            query_result = _response_to_query_result(response, query)
            query_result_all.append(query_result)

        return query_result_all

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
        if delete_all:
            logger.warning("Delete all not supported yet.")
            return False

        if filter is not None:
            logger.warning("Filters are not supported yet.")
            return False

        if ids is not None:
            for id_ in ids:
                try:
                    self._index.delete(id_)
                except NotImplementedError:
                    # NOTE: some indices does not support delete yet.
                    logger.warning(f"{type(self._index)} does not support delete yet.")
                    return False

        return True
