from time import sleep
from typing import Dict, List

import pytest
from datastore.providers.dashvector_datastore import DashVectorDataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    QueryWithEmbedding,
    DocumentMetadataFilter,
    Source,
)

DIM = 1536


@pytest.fixture
def dashvector_datastore():
    return DashVectorDataStore()


@pytest.fixture
def document_chunks() -> Dict[str, List[DocumentChunk]]:
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
        "1929-10-28T09:30:00-05:00",
        "2009-01-03T16:39:57-08:00",
        "2021-01-21T10:00:00-02:00",
    ]
    authors = ["Max Mustermann", "John Doe", "Jane Doe"]

    for i, id in enumerate(ids):
        chunk = DocumentChunk(
            id=id,
            text=texts[i],
            metadata=DocumentChunkMetadata(
                document_id=doc_id,
                source=sources[i],
                source_id=source_ids[i],
                url=urls[i],
                created_at=created_ats[i],
                author=authors[i],
            ),
            embedding=[i] * DIM
        )
        doc_chunks.append(chunk)

    return {doc_id: doc_chunks}


@pytest.mark.asyncio
async def test_upsert(
        dashvector_datastore: DashVectorDataStore,
        document_chunks: Dict[str, List[DocumentChunk]]
) -> None:
    # clear docs
    await dashvector_datastore.delete(delete_all=True)

    # upsert
    doc_ids = await dashvector_datastore._upsert(document_chunks)
    assert doc_ids == list(document_chunks.keys())

    # the vector insert operation is async by design, we wait here a bit for the insertion to complete.
    sleep(1.0)
    stats = dashvector_datastore._collection.stats()

    # assert total doc count
    assert 3 == stats.output.total_doc_count


@pytest.mark.asyncio
async def test_query(
        dashvector_datastore: DashVectorDataStore,
        document_chunks: Dict[str, List[DocumentChunk]]
) -> None:
    # upsert docs
    await dashvector_datastore._upsert(document_chunks)

    # the vector insert operation is async by design, we wait here a bit for the insertion to complete.
    sleep(0.5)
    query = QueryWithEmbedding(
        query="lorem",
        top_k=1,
        embedding=[0] * DIM
    )
    result = await dashvector_datastore._query([query])
    assert 1 == len(result)
    assert 1 == len(result[0].results)
    assert "abc_123" == result[0].results[0].id
    assert "lorem ipsum dolor sit amet" == result[0].results[0].text


@pytest.mark.asyncio
async def test_query_with_date_filter(
        dashvector_datastore: DashVectorDataStore,
        document_chunks: Dict[str, List[DocumentChunk]]
) -> None:
    # upsert docs
    await dashvector_datastore._upsert(document_chunks)

    # the vector insert operation is async by design, we wait here a bit for the insertion to complete.
    sleep(0.5)
    query = QueryWithEmbedding(
        query="lorem",
        filter=DocumentMetadataFilter(
            start_date="2009-01-03T16:39:57-08:00"
        ),
        top_k=3,
        embedding=[0] * DIM
    )
    result = await dashvector_datastore._query([query])
    assert len(result) == 1
    assert len(result[0].results) == 2
    assert {"def_456", "ghi_789"} == {doc.id for doc in result[0].results}
    assert {
               "consectetur adipiscing elit",
               "sed do eiusmod tempor incididunt"
           } == {doc.text for doc in result[0].results}


@pytest.mark.asyncio
async def test_delete_with_ids(
        dashvector_datastore: DashVectorDataStore,
        document_chunks: Dict[str, List[DocumentChunk]]
) -> None:
    # upsert docs
    await dashvector_datastore._upsert(document_chunks)

    # delete with id
    await dashvector_datastore.delete(ids=["abc_123"])

    # the vector insert/delete operation is async by design, we wait here a bit for the insertion to complete.
    sleep(0.5)
    stats = dashvector_datastore._collection.stats()
    assert 2 == stats.output.total_doc_count


@pytest.mark.asyncio
async def test_delete_all(
        dashvector_datastore: DashVectorDataStore,
        document_chunks: Dict[str, List[DocumentChunk]]
) -> None:
    # upsert docs
    await dashvector_datastore._upsert(document_chunks)

    # delete with id
    await dashvector_datastore.delete(delete_all=True)

    # the vector insert/delete operation is async by design, we wait here a bit for the insertion to complete.
    sleep(1.0)
    stats = dashvector_datastore._collection.stats()
    assert 0 == stats.output.total_doc_count


@pytest.mark.asyncio
async def test_delete_with_filter(
        dashvector_datastore: DashVectorDataStore,
        document_chunks: Dict[str, List[DocumentChunk]]
) -> None:
    # upsert docs
    await dashvector_datastore._upsert(document_chunks)
    sleep(0.5)

    # delete with id
    await dashvector_datastore.delete(
        filter=DocumentMetadataFilter(
            start_date="2009-01-03T16:39:57-08:00"
        )
    )

    # the vector insert/delete operation is async by design, we wait here a bit for the insertion to complete.
    sleep(0.5)
    stats = dashvector_datastore._collection.stats()
    assert 1 == stats.output.total_doc_count


