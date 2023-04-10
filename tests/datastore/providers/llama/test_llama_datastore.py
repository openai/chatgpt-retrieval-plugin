from typing import Dict, List
import pytest
from datastore.providers.llama_datastore import LlamaDataStore
from models.models import DocumentChunk, DocumentChunkMetadata, QueryWithEmbedding


def create_embedding(non_zero_pos: int, size: int) -> List[float]:
    vector = [0.0] * size
    vector[non_zero_pos % size] = 1.0
    return vector


@pytest.fixture
def initial_document_chunks() -> Dict[str, List[DocumentChunk]]:
    first_doc_chunks = [
        DocumentChunk(
            id=f"first-doc-{i}",
            text=f"Lorem ipsum {i}",
            metadata=DocumentChunkMetadata(),
            embedding=create_embedding(i, 5),
        )
        for i in range(4, 7)
    ]
    return {
        "first-doc": first_doc_chunks,
    }


@pytest.fixture
def queries() -> List[QueryWithEmbedding]:
    queries = [
        QueryWithEmbedding(
            query='Query 1',
            top_k=1,
            embedding=create_embedding(4, 5),
        ),
        QueryWithEmbedding(
            query='Query 2',
            top_k=2,
            embedding=create_embedding(5, 5),
        ),
    ]
    return queries


@pytest.fixture
def llama_datastore() -> LlamaDataStore:
    return LlamaDataStore()

@pytest.mark.asyncio
async def test_upsert(
    llama_datastore: LlamaDataStore, 
    initial_document_chunks: Dict[str, List[DocumentChunk]]
) -> None:
    """Test basic upsert."""
    doc_ids = await llama_datastore._upsert(initial_document_chunks)
    assert doc_ids == [doc_id for doc_id in initial_document_chunks]


@pytest.mark.asyncio
async def test_query(
    llama_datastore: LlamaDataStore, 
    initial_document_chunks: Dict[str, List[DocumentChunk]],
    queries: List[QueryWithEmbedding],
) -> None:
    """Test basic query."""
    # insert to prepare for test
    await llama_datastore._upsert(initial_document_chunks)

    query_results = await llama_datastore._query(queries)
    assert len(query_results) == len(queries)

    query_0_results = query_results[0].results 
    query_1_results = query_results[1].results

    assert len(query_0_results) == 1
    assert len(query_1_results) == 2
    
    # NOTE: this is the correct behavior
    assert query_0_results[0].id == 'first-doc-4'
    assert query_1_results[0].id == 'first-doc-5'
    assert query_1_results[1].id == 'first-doc-4'


@pytest.mark.asyncio
async def test_delete(
    llama_datastore: LlamaDataStore, 
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
    # insert to prepare for test
    await llama_datastore._upsert(initial_document_chunks)

    is_success = llama_datastore.delete(['first-doc'])
    assert is_success

