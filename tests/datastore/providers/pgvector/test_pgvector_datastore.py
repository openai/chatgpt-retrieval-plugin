import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datastore.providers.pgvector_datastore import (
    PgVectorDataStore,
)
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryWithEmbedding,
)

PGVECTOR_URL = os.getenv("PGVECTOR_URL")
assert PGVECTOR_URL is not None, "PGVECTOR_URL environment variable is not set"

engine = create_engine(PGVECTOR_URL)
Session = sessionmaker(bind=engine)


@pytest.fixture
def pgvector_datastore() -> PgVectorDataStore:
    return PgVectorDataStore(recreate_collection=True)


@pytest.mark.asyncio
async def test_upsert_new_chunk(pgvector_datastore):
    chunk = DocumentChunk(
        id="chunk1",
        text="Sample text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    ids = await pgvector_datastore._upsert({"doc1": [chunk]})
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_upsert_existing_chunk(pgvector_datastore):
    chunk = DocumentChunk(
        id="chunk1",
        text="New text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    ids = await pgvector_datastore._upsert({"doc1": [chunk]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        top_k=1,
    )
    results = await pgvector_datastore._query([query])

    assert len(ids) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].id == "chunk1"
    assert results[0].results[0].text == "New text"


@pytest.mark.asyncio
async def test_query_score(pgvector_datastore):
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
    await pgvector_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
    )
    results = await pgvector_datastore._query([query])

    assert results[0].results[0].id == "chunk1"
    assert int(results[0].results[0].score) == 1


@pytest.mark.asyncio
async def test_query_filter(pgvector_datastore):
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
    await pgvector_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    # Test author filter -- string
    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        filter=DocumentMetadataFilter(author="John"),
    )
    results = await pgvector_datastore._query([query])
    assert results[0].results[0].id == "chunk1"

    # Test source filter -- enum
    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        filter=DocumentMetadataFilter(source="chat"),
    )
    results = await pgvector_datastore._query([query])
    assert results[0].results[0].id == "chunk2"

    # Test created_at filter -- date
    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Query",
        embedding=query_embedding,
        filter=DocumentMetadataFilter(start_date="2022-01-01"),
    )
    results = await pgvector_datastore._query([query])
    assert results[0].results[0].id == "chunk2"


@pytest.mark.asyncio
async def test_delete(pgvector_datastore):
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
    await pgvector_datastore._upsert({"doc1": [chunk1], "doc2": [chunk2]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Another query",
        embedding=query_embedding,
    )
    results = await pgvector_datastore._query([query])

    assert len(results[0].results) == 2
    assert results[0].results[0].id == "chunk1"
    assert results[0].results[1].id == "chunk2"

    await pgvector_datastore.delete(ids=["doc1"])
    results_after_delete = await pgvector_datastore._query([query])

    assert len(results_after_delete[0].results) == 1
    assert results_after_delete[0].results[0].id == "chunk2"


@pytest.mark.asyncio
async def test_delete_all(pgvector_datastore):
    chunk = DocumentChunk(
        id="chunk",
        text="Another text",
        embedding=[1] * 1536,
        metadata=DocumentChunkMetadata(),
    )
    await pgvector_datastore._upsert({"doc": [chunk]})

    query_embedding = [1] * 1536
    query = QueryWithEmbedding(
        query="Another query",
        embedding=query_embedding,
        top_k=1,
    )
    results = await pgvector_datastore._query([query])

    assert len(results) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].id == "chunk"

    await pgvector_datastore.delete(delete_all=True)
    results_after_delete = await pgvector_datastore._query([query])

    assert len(results_after_delete[0].results) == 0
