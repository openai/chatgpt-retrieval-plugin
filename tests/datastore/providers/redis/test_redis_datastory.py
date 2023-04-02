from datastore.providers.redis_datastore import RedisDataStore
import datastore.providers.redis_datastore as static_redis
from models.models import DocumentChunk, DocumentChunkMetadata, QueryWithEmbedding
import pytest
import redis.asyncio as redis
import numpy as np

@pytest.fixture
async def redis_datastore():
    return await RedisDataStore.init()


def create_embedding(i, dim):
    return np.array([i] * dim).astype(np.float64).tolist()

def create_document_chunk(i, dim):
    return DocumentChunk(
        id=f"first-doc_{i}",
        text=f"Lorem ipsum {i}",
        metadata=DocumentChunkMetadata(
            created_at="1970-01-01", document_id=f"doc_{i}"
        ),
        embedding=create_embedding(i, dim),
    )

def create_document_chunks(n, dim):
    docs =  [create_document_chunk(i, dim) for i in range(n)]
    return {"docs": docs}

@pytest.mark.asyncio
async def test_redis_upsert_query(redis_datastore):
    docs = create_document_chunks(10, 5)
    await redis_datastore._upsert(docs)
    query = QueryWithEmbedding(
        query="Lorem ipsum 0",
        top_k=5,
        embedding= create_embedding(1, 5),
    )
    query_results = await redis_datastore._query(queries=[query])
    assert 1 == len(query_results)
    assert "Lorem ipsum 0" == query_results[0].query


