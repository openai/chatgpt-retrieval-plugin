"""
Integration tests of MongoDB Atlas Datastore.

These tests require one to have a running Cluster, Database, Collection and Atlas Search Index
as described in docs/providers/mongodb/setup.md.

One will also have to set the same environment variables. Although one CAN
use we the same collection and index used in examples/providers/mongodb/semantic-search.ipynb,
these tests will make changes to the data, so you may wish to create another collection.
If you have run the example notebook, you can reuse with the following.

MONGODB_DATABASE=SQUAD
MONGODB_COLLECTION=Beyonce
MONGODB_INDEX=vector_index
EMBEDDING_DIMENSION=1536
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>/?retryWrites=true&w=majority
"""


from inspect import iscoroutinefunction
import pytest
import time
from typing import Callable
import os

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



async def assert_when_ready(callable: Callable, tries: int = 5, interval: float = 1):

    for _ in range(tries):
        if iscoroutinefunction(callable):
            print("starting async call")
            result = await callable()
            print(f"finished async call with {result=}")
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
    n_dims = int(os.environ["EMBEDDING_DIMENSION"])
    embedding = [0] * n_dims
    embedding[one_element_poz % n_dims] = 1
    return embedding


def sample_embeddings(num: int, one_element_start: int = 0):
    return [sample_embedding(x + one_element_start) for x in range(num)]


@pytest.fixture
def document_id():
    """ID of an unchunked document"""
    return "a5991f75a315f755c3365ab2"

@pytest.fixture
def chunk_ids(document_id):
    """IDs of chunks"""
    return [f"{document_id}_{i}" for i in range(3)]


@pytest.fixture
def one_documents_chunks(document_id, chunk_ids):
    """Represents output of services.chunks.get_document_chunks
    -> Dict[str, List[DocumentChunk]]
    called on a list containing a single Document
    """

    n_chunks = len(chunk_ids)

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

    embeddings = sample_embeddings(n_chunks)
    doc_chunks = []
    for i in range(n_chunks):
        chunk = DocumentChunk(
            id=chunk_ids[i],
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


async def test_upsert(mongodb_datastore: MongoDBAtlasDataStore, one_documents_chunks, chunk_ids):
    """This tests that data gets uploaded, but not that the search index is built."""
    res = await mongodb_datastore._upsert(one_documents_chunks)
    assert res == chunk_ids

    collection = mongodb_datastore.client[mongodb_datastore.database_name][mongodb_datastore.collection_name]
    await assert_when_ready(collection_size_callback_factory(collection, 3))


async def test_upsert_query_all(mongodb_datastore, one_documents_chunks, chunk_ids):
    """By running _query, this performs """
    res = await mongodb_datastore._upsert(one_documents_chunks)
    await assert_when_ready(lambda: res == chunk_ids)

    query = QueryWithEmbedding(
        query="Aenean",
        top_k=10,
        embedding=sample_embedding(0),  # type: ignore
    )

    async def predicate():
        query_results = await mongodb_datastore._query(queries=[query])
        return 1 == len(query_results) and 3 == len(query_results[0].results)

    await assert_when_ready(predicate, tries=12, interval=5)


async def test_delete_with_document_id(mongodb_datastore, one_documents_chunks, chunk_ids):
    res = await mongodb_datastore._upsert(one_documents_chunks)
    assert res == chunk_ids
    collection = mongodb_datastore.client[mongodb_datastore.database_name][mongodb_datastore.collection_name]
    first_id = str((await collection.find_one())["_id"])
    await mongodb_datastore.delete(ids=[first_id])

    await assert_when_ready(collection_size_callback_factory(collection, 2))

    all_documents = [doc async for doc in collection.find()]
    for document in all_documents:
        assert document["metadata"]["author"] != "Fred Smith"


async def test_delete_with_source_filter(mongodb_datastore, one_documents_chunks, chunk_ids):
    res = await mongodb_datastore._upsert(one_documents_chunks)
    assert res == chunk_ids

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

    await assert_when_ready(predicate, tries=12, interval=5)
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
