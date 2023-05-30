from typing import Dict, List
import os
import pytest
from datastore.providers.cassandra_datastore import CassandraDataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryWithEmbedding,
)
import unittest.mock


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
def cassandra_datastore() -> CassandraDataStore:
    return CassandraDataStore()


@pytest.mark.skip
async def test_upsert_astra(
        cassandra_datastore: CassandraDataStore,
        initial_document_chunks: Dict[str, List[DocumentChunk]],
):
    with unittest.mock.patch.multiple('datastore.providers.cassandra_datastore',
                                      CASSANDRA_PORT=29042,
                                      CASSANDRA_USER= os.environ.get("ASTRA_USER", None),
                                      CASSANDRA_KEYSPACE='vsearch',
                                      CASSANDRA_PASSWORD=os.environ.get("ASTRA_PW", None),
                                      ASTRA_BUNDLE='/home/tato/Downloads/secure-connect-vsearch.zip'
                                      ):
        await test_upsert(cassandra_datastore,initial_document_chunks)

@pytest.mark.asyncio
async def test_upsert(
    cassandra_datastore: CassandraDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
        """Test basic upsert."""
        doc_ids = await cassandra_datastore._upsert(initial_document_chunks)
        assert doc_ids == [doc_id for doc_id in initial_document_chunks]


@pytest.mark.asyncio
async def test_query(
    cassandra_datastore: CassandraDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
    queries: List[QueryWithEmbedding],
) -> None:
    """Test basic query."""
    # todo remove this once we support upserts
    await cassandra_datastore.delete(delete_all=True)
    # insert to prepare for test
    await cassandra_datastore._upsert(initial_document_chunks)

    query_results = await cassandra_datastore._query(queries)
    assert len(query_results) == len(queries)

    query_0_results = query_results[0].results
    query_1_results = query_results[1].results

    assert len(query_0_results) == 1
    assert len(query_1_results) == 2

    # NOTE: this is the correct behavior
    assert query_0_results[0].id == "first-doc-4"
    # TODO flip these if /when we support returning in score order (rather than token order)
    assert query_1_results[0].id == "first-doc-4"
    assert query_1_results[1].id == "first-doc-5"


@pytest.mark.asyncio
async def test_delete(
    cassandra_datastore: CassandraDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
    # insert to prepare for test
    await cassandra_datastore._upsert(initial_document_chunks)

    is_success = await cassandra_datastore.delete(["first-doc"])
    assert is_success


@pytest.mark.asyncio
async def test_upsert_new_chunk(cassandra_datastore):
    await cassandra_datastore.delete(delete_all=True)
    chunk = DocumentChunk(
        id="chunk1",
        text="Sample text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    ids = await cassandra_datastore._upsert({"doc1": [chunk]})
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_upsert_existing_chunk(cassandra_datastore):
    await cassandra_datastore.delete(delete_all=True)
    chunk = DocumentChunk(
        id="chunk1",
        text="Sample text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    ids = await cassandra_datastore._upsert({"doc1": [chunk]})

    chunk = DocumentChunk(
        id="chunk1",
        text="New text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    ids = await cassandra_datastore._upsert({"doc1": [chunk]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        top_k=1,
    )
    results = await cassandra_datastore._query([query])

    assert len(ids) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].id == "chunk1"
    assert results[0].results[0].text == "New text"


@pytest.mark.asyncio
async def test_query_score(cassandra_datastore):
    await cassandra_datastore.delete(delete_all=True)
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
    await cassandra_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
    )
    results = await cassandra_datastore._query([query])

    assert results[0].results[0].id == "chunk1"
    assert int(results[0].results[0].score) == 1536


@pytest.mark.asyncio
async def test_query_filter(cassandra_datastore):
    await cassandra_datastore.delete(delete_all=True)
    chunk1 = DocumentChunk(
        id="chunk1",
        text="Sample text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(
            source="email", created_at="2021-01-01", author="John"
        ),
    )
    chunk2 = DocumentChunk(
        id="chunk2",
        text="Another text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(
            source="chat", created_at="2022-02-02", author="Mike"
        ),
    )
    await cassandra_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    # Test author filter -- string
    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        filter=DocumentMetadataFilter(author="John"),
    )
    results = await cassandra_datastore._query([query])
    assert results[0].results[0].id == "chunk1"

    # Test source filter -- enum
    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        filter=DocumentMetadataFilter(source="chat"),
    )
    results = await cassandra_datastore._query([query])
    assert results[0].results[0].id == "chunk2"

    # Test created_at filter -- date
    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        filter=DocumentMetadataFilter(start_date="2022-01-01"),
    )
    results = await cassandra_datastore._query([query])
    assert results[0].results[0].id == "chunk2"


@pytest.mark.asyncio
async def test_delete(cassandra_datastore):
    await cassandra_datastore.delete(delete_all=True)
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
    await cassandra_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Another query",
        embedding=query_embedding,
    )
    results = await cassandra_datastore._query([query])

    assert len(results[0].results) == 2
    assert any(result.id == "chunk1" for result in results[0].results), "chunk1 is missing."
    assert any(result.id == "chunk2" for result in results[0].results), "chunk2 is missing."

    await cassandra_datastore.delete(ids=["doc1"])
    results_after_delete = await cassandra_datastore._query([query])

    assert len(results_after_delete[0].results) == 1
    assert results_after_delete[0].results[0].id == "chunk2"


@pytest.mark.asyncio
async def test_delete_all(cassandra_datastore):
    await cassandra_datastore.delete(delete_all=True)
    chunk = DocumentChunk(
        id="chunk",
        text="Another text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    await cassandra_datastore._upsert({"doc": [chunk]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Another query",
        embedding=query_embedding,
        top_k=1,
    )
    results = await cassandra_datastore._query([query])

    assert len(results) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].id == "chunk"

    await cassandra_datastore.delete(delete_all=True)
    results_after_delete = await cassandra_datastore._query([query])

    assert len(results_after_delete[0].results) == 0
