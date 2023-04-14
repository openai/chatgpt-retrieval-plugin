from typing import Dict, List
import pytest
from datastore.providers.supabase_datastore import SupabaseDataStore
from models.models import DocumentChunk, DocumentChunkMetadata, QueryWithEmbedding


def create_embedding(non_zero_pos: int) -> List[float]:
    # create a vector with a single non-zero value of dimension 1535
    vector = [0.0] * 1536
    vector[non_zero_pos - 1] = 1.0
    return vector


@pytest.fixture
def initial_document_chunks() -> Dict[str, List[DocumentChunk]]:
    first_doc_chunks = [
        DocumentChunk(
            id=f"first-doc-{i}",
            text=f"Lorem ipsum {i}",
            metadata=DocumentChunkMetadata(),
            embedding=create_embedding(i),
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
            query="Query 1",
            top_k=1,
            embedding=create_embedding(4),
        ),
        QueryWithEmbedding(
            query="Query 2",
            top_k=2,
            embedding=create_embedding(5),
        ),
    ]
    return queries


@pytest.fixture
def supabase_datastore() -> SupabaseDataStore:
    return SupabaseDataStore()


@pytest.mark.asyncio
async def test_upsert(
    supabase_datastore: SupabaseDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
    """Test basic upsert."""
    doc_ids = await supabase_datastore._upsert(initial_document_chunks)
    assert doc_ids == [doc_id for doc_id in initial_document_chunks]


@pytest.mark.asyncio
async def test_query(
    supabase_datastore: SupabaseDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
    queries: List[QueryWithEmbedding],
) -> None:
    """Test basic query."""
    # insert to prepare for test
    await supabase_datastore._upsert(initial_document_chunks)

    query_results = await supabase_datastore._query(queries)
    assert len(query_results) == len(queries)

    query_0_results = query_results[0].results
    query_1_results = query_results[1].results

    assert len(query_0_results) == 1
    assert len(query_1_results) == 2

    # NOTE: this is the correct behavior
    assert query_0_results[0].id == "first-doc-4"
    assert query_1_results[0].id == "first-doc-5"
    assert query_1_results[1].id == "first-doc-4"


@pytest.mark.asyncio
async def test_delete(
    supabase_datastore: SupabaseDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
    # insert to prepare for test
    await supabase_datastore._upsert(initial_document_chunks)

    is_success = await supabase_datastore.delete(["first-doc"])
    assert is_success
