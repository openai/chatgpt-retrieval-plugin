import pytest
from models.models import (
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    DocumentChunk,
    QueryWithEmbedding,
    Source,
)
from datastore.providers.elasticsearch_datastore import (
    ElasticsearchDataStore,
)
import time
import os

DIM_SIZE = int(os.environ.get("EMBEDDING_DIMENSION", 256))


@pytest.fixture
def elasticsearch_datastore():
    return ElasticsearchDataStore()


def sample_embedding(one_element_poz: int):
    embedding = [0] * DIM_SIZE
    embedding[one_element_poz % DIM_SIZE] = 1
    return embedding


def sample_embeddings(num: int, one_element_start: int = 0):
    embeddings = []
    for x in range(num):
        embedding = [0] * DIM_SIZE
        embedding[(x + one_element_start) % DIM_SIZE] = 1
        embeddings.append(embedding)
    return embeddings


@pytest.fixture
def document_chunk_one():
    doc_id = "abc"
    doc_chunks = []

    ids = ["123", "456", "789"]
    texts = [
        "Aenean euismod bibendum laoreet",
        "Vivamus non enim vitae tortor",
        "Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae",
    ]
    sources = [Source.email, Source.file, Source.chat]
    created_ats = [
        "1929-10-28T09:30:00-05:00",
        "2009-01-03T16:39:57-08:00",
        "2021-01-21T10:00:00-02:00",
    ]
    authors = ["Fred Smith", "Bob Doe", "Appleton Doe"]

    embeddings = sample_embeddings(len(texts))

    for i in range(3):
        chunk = DocumentChunk(
            id=ids[i],
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id,
                source=sources[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks.append(chunk)

    return {doc_id: doc_chunks}


async def test_upsert(elasticsearch_datastore, document_chunk_one):
    await elasticsearch_datastore.delete(delete_all=True)
    res = await elasticsearch_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    time.sleep(1)

    results = elasticsearch_datastore.client.search(
        index=elasticsearch_datastore.index_name, query={"match_all": {}}
    )
    assert results["hits"]["total"]["value"] == 3
    elasticsearch_datastore.client.indices.delete(
        index=elasticsearch_datastore.index_name
    )


async def test_upsert_query_all(elasticsearch_datastore, document_chunk_one):
    await elasticsearch_datastore.delete(delete_all=True)
    res = await elasticsearch_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    time.sleep(1)

    query = QueryWithEmbedding(
        query="Aenean",
        top_k=10,
        embedding=sample_embedding(0),  # type: ignore
    )
    query_results = await elasticsearch_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 3 == len(query_results[0].results)


async def test_delete_with_document_id(elasticsearch_datastore, document_chunk_one):
    await elasticsearch_datastore.delete(delete_all=True)
    res = await elasticsearch_datastore._upsert(document_chunk_one)
    time.sleep(1)
    assert res == list(document_chunk_one.keys())
    await elasticsearch_datastore.delete([res[0]])
    time.sleep(1)

    query = QueryWithEmbedding(
        query="Aenean",
        top_k=9,
        embedding=sample_embedding(0),  # type: ignore
    )
    query_results = await elasticsearch_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 0 == len(query_results[0].results)

    elasticsearch_datastore.client.indices.delete(
        index=elasticsearch_datastore.index_name
    )


async def test_delete_with_source_filter(elasticsearch_datastore, document_chunk_one):
    await elasticsearch_datastore.delete(delete_all=True)
    res = await elasticsearch_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    time.sleep(1)

    await elasticsearch_datastore.delete(
        filter=DocumentMetadataFilter(
            source=Source.email,
        )
    )

    time.sleep(1)

    query = QueryWithEmbedding(
        query="Aenean",
        top_k=9,
        embedding=sample_embedding(0),  # type: ignore
    )
    query_results = await elasticsearch_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 2 == len(query_results[0].results)
    assert "456" == query_results[0].results[0].id

    elasticsearch_datastore.client.indices.delete(
        index=elasticsearch_datastore.index_name
    )
