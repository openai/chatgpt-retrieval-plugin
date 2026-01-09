import numpy as np
import pytest
from datastore.providers.valkey_datastore import ValkeyDataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    QueryWithEmbedding,
    Source,
    DocumentMetadataFilter,
)

NUM_TEST_DOCS = 10


def create_embedding(i, dim):
    vec = np.array([0.1] * dim).astype(np.float32).tolist()
    vec[dim - 1] = i + 1 / 10
    return vec


def create_document_chunk(i, dim):
    return DocumentChunk(
        id=f"first-doc_{i}",
        text=f"Lorem ipsum {i}",
        embedding=create_embedding(i, dim),
        metadata=DocumentChunkMetadata(
            source=Source.file, created_at="1970-01-01", document_id="docs"
        ),
    )


def create_document_chunks(n, dim):
    docs = [create_document_chunk(i, dim) for i in range(n)]
    return {"docs": docs}


@pytest.mark.asyncio
async def test_valkey_upsert_query():
    valkey_datastore = await ValkeyDataStore.init(dim=5)
    await valkey_datastore.drop_index()
    valkey_datastore = await ValkeyDataStore.init(dim=5)
    docs = create_document_chunks(NUM_TEST_DOCS, 5)
    await valkey_datastore._upsert(docs)
    query = QueryWithEmbedding(
        query="Lorem ipsum 0",
        top_k=5,
        embedding=create_embedding(0, 5),
    )
    query_results = await valkey_datastore._query(queries=[query])
    assert 1 == len(query_results)
    for i in range(5):
        assert f"Lorem ipsum {i}" == query_results[0].results[i].text
        assert "docs" == query_results[0].results[i].id


@pytest.mark.asyncio
async def test_valkey_filter_query():
    valkey_datastore = await ValkeyDataStore.init(dim=5)
    query = QueryWithEmbedding(
        query="Lorem ipsum 0",
        filter=DocumentMetadataFilter(document_id="docs"),
        top_k=5,
        embedding=create_embedding(0, 5),
    )
    query_results = await valkey_datastore._query(queries=[query])
    print(query_results)
    assert 1 == len(query_results)
    assert "docs" == query_results[0].results[0].id


@pytest.mark.asyncio
async def test_valkey_delete_docs():
    valkey_datastore = await ValkeyDataStore.init(dim=5)
    res = await valkey_datastore.delete(ids=["docs"])
    assert res
