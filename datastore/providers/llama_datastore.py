import json
import os
from typing import Dict, List, Optional
from loguru import logger
from datastore.datastore import DataStore
from models.models import DocumentChunk, DocumentChunkMetadata, DocumentChunkWithScore, DocumentMetadataFilter, QueryResult, QueryWithEmbedding

# TODO: import all supported indices
from llama_index import GPTTreeIndex, GPTListIndex, GPTSimpleVectorIndex, Document
from llama_index.indices.knowledge_graph import GPTKnowledgeGraphIndex
from llama_index.indices.base import BaseGPTIndex
from llama_index.indices.query.schema import QueryBundle

INDEX_TYPE = os.environ.get('LLAMA_INDEX_TYPE', 'simple_vector')
INDEX_JSON_PATH = os.environ.get('LLAMA_INDEX_JSON_PATH', None)
QUERY_CONFIG_JSON_PATH = os.environ.get('LLAMA_QUERY_CONFIG_JSON_PATH', None)
RESPONSE_MODE = 'no_text'


# TODO: support more indices
# Hardcoded mapping from index type str to index class
INDEX_TYPE_TO_INDEX_CLS: Dict[str, BaseGPTIndex] = {
    'tree': GPTTreeIndex,
    'list': GPTListIndex,
    'simple_vector': GPTSimpleVectorIndex,
    'kg': GPTKnowledgeGraphIndex,
}

def get_index_cls(index_type: str) -> BaseGPTIndex:
    """Get index class from index type str."""
    if index_type not in INDEX_TYPE_TO_INDEX_CLS:
        raise ValueError(f'Unknown index type: {index_type}')
    return INDEX_TYPE_TO_INDEX_CLS[index_type]


class LlamaDataStore(DataStore):
    def __init__(self):
        index_cls = get_index_cls(INDEX_TYPE)
        if INDEX_JSON_PATH is None:
            # Create empty index
            self._index = index_cls(documents=[])
        else:
            # Load index from disk
            self._index = index_cls.load_from_disk(INDEX_JSON_PATH)
        
        if QUERY_CONFIG_JSON_PATH is None:
            self._query_configs = None
        else: 
            with open(INDEX_JSON_PATH, 'r') as f:
                self._query_configs = json.load(f)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """
        # TODO: right now will always insert instead of updating
        doc_ids = []
        for doc_id, doc_chunks in chunks.items():
            logger.debug(f"Upserting {doc_id} with {len(doc_chunks)} chunks")
            for doc_chunk in doc_chunks:
                document = Document(
                    # TODO: right now all chunks would have the same doc id
                    doc_id=doc_id,
                    text=doc_chunk.text,
                    embedding=doc_chunk.embedding,
                    extra_info=doc_chunk.metadata.dict()
                )
                self._index.insert(document)
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
        # TODO: filters are not supported
        query_result_all = []
        for query in queries:
            query_bundle = QueryBundle(
                query_str = query.query,
                embedding=query.embedding,
            )
            # similarity_top_k = query.top_k
            if self._query_configs is not None:
                response = await self._index.aquery(query_bundle, response_mode=RESPONSE_MODE, query_configs=self._query_configs)
            else:
                response = await self._index.aquery(query_bundle, response_mode=RESPONSE_MODE)
            results = []
            for node in response.source_nodes:
                result = DocumentChunkWithScore(
                    id=node.doc_id,
                    text=node.source_text,
                    score=node.similarity if node.similarity is not None else 1.,
                    metadata=DocumentChunkMetadata(**node.extra_info) if node.extra_info is not None else DocumentChunkMetadata(),
                )
                results.append(result)
            query_result = QueryResult(
                query=query.query,
                results=results,
            )
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
        # TODO: filters are not supported
        # TODO: delete all is not supported
        if ids is not None:
            for id_ in ids:
                self._index.delete(id_)
        return False