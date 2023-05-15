from typing import Dict, List
import pytest
from datastore.providers.postgresml_datastore import PostgresMLDataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryWithEmbedding,
)


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
def postgresml_datastore() -> PostgresMLDataStore:
    return PostgresMLDataStore()


@pytest.mark.asyncio
async def test_upsert(
    postgresml_datastore: PostgresMLDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
    """Test basic upsert."""
    doc_ids = await postgresml_datastore._upsert(initial_document_chunks)
    print(doc_ids)
    assert doc_ids == [doc_id for doc_id in initial_document_chunks]


@pytest.mark.asyncio
async def test_query(
    postgresml_datastore: PostgresMLDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
    queries: List[QueryWithEmbedding],
) -> None:
    """Test basic query."""
    # insert to prepare for test
    
    query_results = await postgresml_datastore._query(queries)
    assert len(query_results) == len(queries)

    query_0_results = query_results[0].results
    query_1_results = query_results[1].results

    assert len(query_0_results) == 1
    assert len(query_1_results) == 2
    print(query_1_results)
    # NOTE: this is the correct behavior
    assert query_0_results[0].id == "first-doc-4"
    assert query_1_results[0].id == "first-doc-5"
    assert query_1_results[1].id == "first-doc-4"


@pytest.mark.asyncio
async def test_delete(
    postgresml_datastore: PostgresMLDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
    # insert to prepare for test
    await postgresml_datastore._upsert(initial_document_chunks)

    is_success = await postgresml_datastore.delete(["first-doc"])
    assert is_success


@pytest.mark.asyncio
async def test_upsert_new_chunk(postgresml_datastore):
    await postgresml_datastore.delete(delete_all=True)
    chunk = DocumentChunk(
        id="chunk1",
        text="Sample text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    ids = await postgresml_datastore._upsert({"doc1": [chunk]})
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_query_score(postgresml_datastore):
    await postgresml_datastore.delete(delete_all=True)
    chunk1 = DocumentChunk(
        id="chunk1",
        text="Sample text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    chunk2 = DocumentChunk(
        id="chunk2",
        text="Another text",
        embedding=[-1 if i % 2 == 0 else 1 for i in range(1536)],
        metadata=DocumentChunkMetadata(),
    )
    await postgresml_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
    )
    results = await postgresml_datastore._query([query])

    assert results[0].results[0].id == "chunk1"
    assert int(results[0].results[0].score) == 1

@pytest.mark.asyncio
async def test_delete(postgresml_datastore):
    await postgresml_datastore.delete(delete_all=True)
    chunk1 = DocumentChunk(
        id="chunk1",
        text="Sample text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    chunk2 = DocumentChunk(
        id="chunk2",
        text="Another text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    await postgresml_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Another query",
        embedding=query_embedding,
    )
    results = await postgresml_datastore._query([query])

    assert len(results[0].results) == 2
    assert results[0].results[0].id == "chunk1"
    assert results[0].results[1].id == "chunk2"

    await postgresml_datastore.delete(ids=["doc1"])
    results_after_delete = await postgresml_datastore._query([query])

    assert len(results_after_delete[0].results) == 1
    assert results_after_delete[0].results[0].id == "chunk2"


@pytest.mark.asyncio
async def test_delete_all(postgresml_datastore):
    await postgresml_datastore.delete(delete_all=True)
    chunk = DocumentChunk(
        id="chunk",
        text="Another text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    await postgresml_datastore._upsert({"doc": [chunk]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Another query",
        embedding=query_embedding,
        top_k=1,
    )
    results = await postgresml_datastore._query([query])

    assert len(results) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].id == "chunk"

    await postgresml_datastore.delete(delete_all=True)
    results_after_delete = await postgresml_datastore._query([query])

    assert len(results_after_delete[0].results) == 0
