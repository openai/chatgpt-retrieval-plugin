import numpy as np
import pytest

"""
import os
os.environ["TAIR_HOST"] = "localhost"
os.environ["TAIR_PORT"] = "6379"
os.environ["TAIR_USERNAME"] = "user"
os.environ["TAIR_PASSWORD"] = "passwd"
"""

from datastore.providers.tair_datastore import TairDataStore
from datastore.providers.tair_datastore import VECTOR_DIMENSION
from models.models import DocumentChunk, DocumentChunkMetadata, QueryWithEmbedding, Source, DocumentMetadataFilter

NUM_TEST_DOC_CHUNKS = 10
TOP_K = 5
DOC_ID = "first-doc"


@pytest.fixture
def tair_datastore():
    return TairDataStore()


def create_embedding(i, dim):
    vec = np.array([0] * dim).astype(np.float64).tolist()
    vec[i] = 1
    return vec


def create_document_chunk(doc_id, i, dim):
    return DocumentChunk(
        id=f"{doc_id}_{i}",
        text=f"Lorem ipsum {i}",
        embedding=create_embedding(i, dim),
        metadata=DocumentChunkMetadata(
            source=Source.file, created_at="2023-06-01", document_id=doc_id,
            source_id="default",
            url="https://www.alibabacloud.com/help/en/tair/latest/tairvector"
        ),
    )


def create_document_chunks(n, dim):
    doc_chunks = [create_document_chunk(DOC_ID, i, dim) for i in range(n)]
    return {DOC_ID: doc_chunks}


@pytest.mark.asyncio
async def test_tair_upsert_query(tair_datastore):
    doc_chunks = create_document_chunks(NUM_TEST_DOC_CHUNKS, VECTOR_DIMENSION)
    await tair_datastore._upsert(doc_chunks)
    query = QueryWithEmbedding(
        query="Lorem ipsum 0",
        top_k=TOP_K,
        embedding=create_embedding(0, VECTOR_DIMENSION),
    )
    query_results = await tair_datastore._query(queries=[query])
    assert 1 == len(query_results)
    assert TOP_K == len(query_results[0].results)
    for i in range(TOP_K):
        if i == 0:
            assert f"Lorem ipsum {i}" == query_results[0].results[i].text
        assert DOC_ID == query_results[0].results[i].id


@pytest.mark.asyncio
async def test_tair_filter_query(tair_datastore):
    query = QueryWithEmbedding(
        query="Lorem ipsum 0",
        filter=DocumentMetadataFilter(document_id=DOC_ID),
        top_k=TOP_K,
        embedding=create_embedding(0, VECTOR_DIMENSION),
    )
    query_results = await tair_datastore._query(queries=[query])
    assert 1 == len(query_results)
    assert TOP_K == len(query_results[0].results)
    for i in range(TOP_K):
        if i == 0:
            assert f"Lorem ipsum {i}" == query_results[0].results[i].text
        assert DOC_ID == query_results[0].results[i].id


@pytest.mark.asyncio
async def test_tair_filter_none_query(tair_datastore):
    query = QueryWithEmbedding(
        query="Lorem ipsum 0",
        filter=DocumentMetadataFilter(source=Source.chat),
        top_k=TOP_K,
        embedding=create_embedding(0, VECTOR_DIMENSION),
    )
    query_results = await tair_datastore._query(queries=[query])
    assert 1 == len(query_results)
    assert 0 == len(query_results[0].results)


@pytest.mark.asyncio
async def test_tair_delete_docs_by_ids(tair_datastore):
    res = await tair_datastore.delete(ids=[DOC_ID])
    assert res


@pytest.mark.asyncio
async def test_tair_delete_index(tair_datastore):
    res = await tair_datastore.delete(delete_all=True)
    assert res


@pytest.mark.asyncio
async def test_tair_delete_docs_by_filter(tair_datastore):
    filter = DocumentMetadataFilter(document_id=DOC_ID)
    res = await tair_datastore.delete(filter=filter)
    assert res
