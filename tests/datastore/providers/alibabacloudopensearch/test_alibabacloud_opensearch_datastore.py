import time

import pytest
from models.models import (
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    DocumentChunk,
    QueryWithEmbedding,
    Source,
)
from datastore.providers.alibabacloud_opensearch_datastore import (
    OUTPUT_DIM,
    AlibabaCloudOpenSearchDataStore,
)
import datetime

@pytest.fixture
def opensearch_datastore():
    return AlibabaCloudOpenSearchDataStore()

@pytest.fixture
def document_chunk_one():
    doc_id = "zerp"
    doc_chunks = []

    ids = ["abc_123", "def_456", "ghi_789"]
    texts = [
        "lorem ipsum dolor sit amet",
        "consectetur adipiscing elit",
        "sed do eiusmod tempor incididunt",
    ]
    sources = [Source.email, Source.file, Source.chat]
    source_ids = ["foo", "bar", "baz"]
    urls = ["foo.com", "bar.net", "baz.org"]
    created_ats = [
        int(datetime.datetime.fromisoformat("1929-10-28T09:30:00-05:00").timestamp()),
        int(datetime.datetime.fromisoformat("2009-01-03T16:39:57-08:00").timestamp()),
        int(datetime.datetime.fromisoformat("2021-01-21T10:00:00-02:00").timestamp())
    ]
    authors = ["Max Mustermann", "John Doe", "Jane Doe"]
    embeddings = [[x] * OUTPUT_DIM for x in range(3)]

    for i in range(3):
        chunk = DocumentChunk(
            id=ids[i],
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id,
                source=sources[i],
                source_id=source_ids[i],
                url=urls[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks.append(chunk)

    return {doc_id: doc_chunks}


@pytest.fixture
def document_chunk_two():
    doc_id_1 = "zerp"
    doc_chunks_1 = []

    ids = ["abc_123", "def_456", "ghi_789"]
    texts = [
        "1lorem ipsum dolor sit amet",
        "2consectetur adipiscing elit",
        "3sed do eiusmod tempor incididunt",
    ]
    sources = [Source.email, Source.file, Source.chat]
    source_ids = ["foo", "bar", "baz"]
    urls = ["foo.com", "bar.net", "baz.org"]
    created_ats = [
        "1929-10-28T09:30:00-05:00",
        "2009-01-03T16:39:57-08:00",
        "3021-01-21T10:00:00-02:00",
    ]
    authors = ["Max Mustermann", "John Doe", "Jane Doe"]
    embeddings = [[x] * OUTPUT_DIM for x in range(3)]

    for i in range(3):
        chunk = DocumentChunk(
            id=ids[i],
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id_1,
                source=sources[i],
                source_id=source_ids[i],
                url=urls[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks_1.append(chunk)

    doc_id_2 = "merp"
    doc_chunks_2 = []

    ids = ["jkl_123", "lmn_456", "opq_789"]
    texts = [
        "3sdsc efac feas sit qweas",
        "4wert sdfas fdsc",
        "52dsc fdsf eiusmod asdasd incididunt",
    ]
    sources = [Source.email, Source.file, Source.chat]
    source_ids = ["foo", "bar", "baz"]
    urls = ["foo.com", "bar.net", "baz.org"]
    created_ats = [
        "4929-10-28T09:30:00-05:00",
        "5009-01-03T16:39:57-08:00",
        "6021-01-21T10:00:00-02:00",
    ]
    authors = ["Max Mustermann", "John Doe", "Jane Doe"]
    embeddings = [[x] * OUTPUT_DIM for x in range(3, 6)]

    for i in range(3):
        chunk = DocumentChunk(
            id=ids[i],
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id_2,
                source=sources[i],
                source_id=source_ids[i],
                url=urls[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=embeddings[i],  # type: ignore
        )

        doc_chunks_2.append(chunk)

    return {doc_id_1: doc_chunks_1, doc_id_2: doc_chunks_2}


@pytest.mark.asyncio
async def test_upsert(opensearch_datastore, document_chunk_one):
    await delete_all(opensearch_datastore)
    res = await opensearch_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    time.sleep(1)

    query = QueryWithEmbedding(
        query="lorem",
        top_k=10,
        embedding=[0.5] * OUTPUT_DIM,
    )
    query_results = await opensearch_datastore._query(queries=[query])
    assert 3 == len(query_results[0].results)

@pytest.mark.asyncio
async def test_reload(opensearch_datastore, document_chunk_one, document_chunk_two):
    await delete_all(opensearch_datastore)
    res = await opensearch_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    time.sleep(1)

    query = QueryWithEmbedding(
        query="lorem",
        top_k=10,
        embedding=[0.5] * OUTPUT_DIM,
    )

    query_results = await opensearch_datastore._query(queries=[query])
    assert 3 == len(query_results[0].results)
    new_store = AlibabaCloudOpenSearchDataStore()
    another_in = {i: document_chunk_two[i] for i in document_chunk_two if i != res[0]}
    res = await new_store._upsert(another_in)
    time.sleep(1)

    query_results = await opensearch_datastore._query(queries=[query])
    assert 1 == len(query_results)
    assert 6 == len(query_results[0].results)


@pytest.mark.asyncio
async def test_upsert_query_all(opensearch_datastore, document_chunk_two):
    await delete_all(opensearch_datastore)
    res = await opensearch_datastore._upsert(document_chunk_two)
    assert res == list(document_chunk_two.keys())
    time.sleep(1)

    # Num entities currently doesn't track deletes
    query = QueryWithEmbedding(
        query="lorem",
        top_k=10,
        embedding=[0.5] * OUTPUT_DIM,
    )
    query_results = await opensearch_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 6 == len(query_results[0].results)


@pytest.mark.asyncio
async def test_query_accuracy(opensearch_datastore, document_chunk_one):
    await delete_all(opensearch_datastore)
    res = await opensearch_datastore._upsert(document_chunk_one)
    time.sleep(1)

    assert res == list(document_chunk_one.keys())
    query = QueryWithEmbedding(
        query="lorem",
        top_k=1,
        embedding=[0] * OUTPUT_DIM,
    )
    query_results = await opensearch_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert 10000 == query_results[0].results[0].score
    assert "abc_123" == query_results[0].results[0].id

@pytest.mark.asyncio
async def test_query_filter(opensearch_datastore, document_chunk_one):
    await delete_all(opensearch_datastore)
    res = await opensearch_datastore._upsert(document_chunk_one)
    time.sleep(1)

    assert res == list(document_chunk_one.keys())
    query = QueryWithEmbedding(
        query="lorem",
        top_k=1,
        embedding=[0] * OUTPUT_DIM,
        filter=DocumentMetadataFilter(
            start_date="2000-01-03T16:39:57-08:00", end_date="2010-01-03T16:39:57-08:00"
        ),
    )
    query_results = await opensearch_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert 0 != query_results[0].results[0].score
    assert "def_456" == query_results[0].results[0].id

    query = QueryWithEmbedding(
        query="lorem",
        top_k=1,
        embedding=[0] * OUTPUT_DIM,
        filter=DocumentMetadataFilter(
            source="chat"
        ),
    )
    query_results = await opensearch_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert 0 != query_results[0].results[0].score
    assert "ghi_789" == query_results[0].results[0].id


@pytest.mark.xfail(raises=Exception)
def test_delete_all(opensearch_datastore, document_chunk_one):
    opensearch_datastore.delete(delete_all=True)

@pytest.mark.xfail(raises=Exception)
def test_delete_with_filter(opensearch_datastore, document_chunk_one):
    opensearch_datastore.delete(
        filter=DocumentMetadataFilter(
            end_date="2009-01-03T16:39:57-08:00",
        )
    )

async def delete_all(opensearch_datastore):
    await opensearch_datastore.delete(ids=["abc_123", "def_456", "ghi_789", "jkl_123", "lmn_456", "opq_789"])
