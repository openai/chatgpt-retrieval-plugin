import asyncio
from inspect import iscoroutinefunction
import pytest
import time
from typing import Callable

from models.models import (
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    DocumentChunk,
    QueryWithEmbedding,
    Source,
)
from services.date import to_unix_timestamp
from datetime import datetime
from datastore.providers.mongodb_atlas_datastore import (
    MongoDBAtlasDataStore,
)


DIM_SIZE = 1536


async def assert_when_ready(callable: Callable, tries: int = 5, interval: float = 1):
    for _ in range(tries):
        if iscoroutinefunction(callable):
            result = await callable()
        else:
            result = callable()
        if result:
            return
        time.sleep(interval)

    raise AssertionError("Condition not met after multiple attempts")


def collection_size_callback_factory(collection, num: int):

    async def predicate():
        num_documents = await collection.count_documents({})
        return num_documents == num

    return predicate


@pytest.fixture
def _mongodb_datastore():
    return MongoDBAtlasDataStore()


@pytest.fixture
async def mongodb_datastore(_mongodb_datastore):
    await _mongodb_datastore.delete(delete_all=True)
    collection = _mongodb_datastore.client[_mongodb_datastore.database_name][_mongodb_datastore.collection_name]
    await assert_when_ready(collection_size_callback_factory(collection, 0))
    yield _mongodb_datastore
    await _mongodb_datastore.delete(delete_all=True)
    await assert_when_ready(collection_size_callback_factory(collection, 0))


def sample_embedding(one_element_poz: int):
    embedding = [0] * DIM_SIZE
    embedding[one_element_poz % DIM_SIZE] = 1
    return embedding


def sample_embeddings(num: int, one_element_start: int = 0):
    return [sample_embedding(x + one_element_start) for x in range(num)]


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
    await assert_when_ready(collection_size_callback_factory(collection, 3))


async def test_upsert_query_all(mongodb_datastore, document_chunk_one):
    res = await mongodb_datastore._upsert(document_chunk_one)
    await assert_when_ready(lambda: res == list(document_chunk_one.keys()))

    query = QueryWithEmbedding(
        query="Aenean",
        top_k=10,
        embedding=sample_embedding(0),  # type: ignore
    )

    async def predicate():
        query_results = await mongodb_datastore._query(queries=[query])
        return 1 == len(query_results) and 3 == len(query_results[0].results)

    await assert_when_ready(predicate)


async def test_delete_with_document_id(mongodb_datastore, document_chunk_one):
    res = await mongodb_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    collection = mongodb_datastore.client[mongodb_datastore.database_name][mongodb_datastore.collection_name]
    first_id = str((await collection.find_one())["_id"])
    await mongodb_datastore.delete(ids=[first_id])

    await assert_when_ready(collection_size_callback_factory(collection, 2))

    all_documents = [doc async for doc in collection.find()]
    for document in all_documents:
        assert document["metadata"]["author"] != "Fred Smith"


async def test_delete_with_source_filter(mongodb_datastore, document_chunk_one):
    res = await mongodb_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())

    await mongodb_datastore.delete(
        filter=DocumentMetadataFilter(
            source=Source.email,
        )
    )

    query = QueryWithEmbedding(
        query="Aenean",
        top_k=9,
        embedding=sample_embedding(0),  # type: ignore
    )

    async def predicate():
        query_results = await mongodb_datastore._query(queries=[query])
        return 1 == len(query_results) and query_results[0].results

    await assert_when_ready(predicate)
    query_results = await mongodb_datastore._query(queries=[query])
    for result in query_results[0].results:
        assert result.text != "Aenean euismod bibendum laoreet"


@pytest.fixture
def build_mongo_filter():
    return MongoDBAtlasDataStore()._build_mongo_filter


async def test_build_mongo_filter_with_no_filter(build_mongo_filter):
    result = build_mongo_filter()
    assert result == {}


async def test_build_mongo_filter_with_start_date(build_mongo_filter):
    date = datetime(2022, 1, 1).isoformat()
    filter_data = {"start_date": date}
    result = build_mongo_filter(DocumentMetadataFilter(**filter_data))

    assert result == {
        "$and": [
            {"created_at": {"$gte": to_unix_timestamp(date)}}
        ]
    }


async def test_build_mongo_filter_with_end_date(build_mongo_filter):
    date = datetime(2022, 1, 1).isoformat()
    filter_data = {"end_date": date}
    result = build_mongo_filter(DocumentMetadataFilter(**filter_data))

    assert result == {
        "$and": [
            {"created_at": {"$lte": to_unix_timestamp(date)}}
        ]
    }


async def test_build_mongo_filter_with_metadata_field(build_mongo_filter):
    filter_data = {"source": "email"}
    result = build_mongo_filter(DocumentMetadataFilter(**filter_data))

    assert result == {
        "$and": [
            {"metadata.source": "email"}
        ]
    }
