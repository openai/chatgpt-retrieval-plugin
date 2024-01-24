import pytest
from models.models import (
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    DocumentChunk,
    QueryWithEmbedding,
    Source,
)
from datastore.providers.mongodb_atlas_datastore import (
    MongoDBAtlasDataStore,
)
import asyncio

DIM_SIZE = 1536


@pytest.fixture
def _mongodb_datastore():
    return MongoDBAtlasDataStore()


@pytest.fixture
async def mongodb_datastore(_mongodb_datastore):
    await _mongodb_datastore.delete(delete_all=True)
    await asyncio.sleep(1)
    yield _mongodb_datastore
    await _mongodb_datastore.delete(delete_all=True)


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
    document_id = "a5991f75a315f755c3365ab2"
    doc_chunks = []

    ids = [
        "659ecbb2b1a47b36f140167f",
        "659ecbb2b1a47b36f1401680",
        "659ecbb2b1a47b36f1401681"]
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
                document_id=document_id,
                source=sources[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks.append(chunk)

    return {document_id: doc_chunks}


async def test_upsert(mongodb_datastore, document_chunk_one):
    res = await mongodb_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    collection = mongodb_datastore.client[mongodb_datastore.database_name][mongodb_datastore.collection_name]
    num_documents = await collection.count_documents({})
    assert num_documents == 3


async def test_upsert_query_all(mongodb_datastore, document_chunk_one):
    res = await mongodb_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    await asyncio.sleep(2)

    query = QueryWithEmbedding(
        query="Aenean",
        top_k=10,
        embedding=sample_embedding(0),  # type: ignore
    )
    query_results = await mongodb_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 3 == len(query_results[0].results)


async def test_delete_with_document_id(mongodb_datastore, document_chunk_one):
    res = await mongodb_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    collection = mongodb_datastore.client[mongodb_datastore.database_name][mongodb_datastore.collection_name]
    first_id = str((await collection.find_one())["_id"])
    await mongodb_datastore.delete(ids=[first_id])

    all_documents = [doc async for doc in collection.find()]
    num_documents = await collection.count_documents({})

    assert 2 == num_documents
    assert all_documents[0]["metadata"]["author"] != "Fred Smith"
    assert all_documents[1]["metadata"]["author"] != "Fred Smith"


async def test_delete_with_source_filter(mongodb_datastore, document_chunk_one):
    res = await mongodb_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    await asyncio.sleep(0.5)

    await mongodb_datastore.delete(
        filter=DocumentMetadataFilter(
            source=Source.email,
        )
    )
    await asyncio.sleep(2)
    query = QueryWithEmbedding(
        query="Aenean",
        top_k=9,
        embedding=sample_embedding(0),  # type: ignore
    )
    query_results = await mongodb_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 2 == len(query_results[0].results)
    assert query_results[0].results[0].text != "Aenean euismod bibendum laoreet"
    assert query_results[0].results[1].text != "Aenean euismod bibendum laoreet"
