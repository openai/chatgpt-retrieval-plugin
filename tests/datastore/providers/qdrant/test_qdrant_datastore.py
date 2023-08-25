from typing import Dict, List

import pytest
import qdrant_client
from qdrant_client.http.models import PayloadSchemaType

from datastore.providers.qdrant_datastore import QdrantDataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    QueryWithEmbedding,
    DocumentMetadataFilter,
    Source,
)


def create_embedding(non_zero_pos: int, size: int) -> List[float]:
    vector = [0.0] * size
    vector[non_zero_pos % size] = 1.0
    return vector


@pytest.fixture
def qdrant_datastore() -> QdrantDataStore:
    return QdrantDataStore(
        collection_name="documents", vector_size=5, recreate_collection=True
    )


@pytest.fixture
def client() -> qdrant_client.QdrantClient:
    return qdrant_client.QdrantClient()


@pytest.fixture
def initial_document_chunks() -> Dict[str, List[DocumentChunk]]:
    first_doc_chunks = [
        DocumentChunk(
            id=f"first-doc-{i}",
            text=f"Lorem ipsum {i}",
            metadata=DocumentChunkMetadata(),
            embedding=create_embedding(i, 5),
        )
        for i in range(4, 7)
    ]
    return {
        "first-doc": first_doc_chunks,
    }


@pytest.fixture
def document_chunks() -> Dict[str, List[DocumentChunk]]:
    first_doc_chunks = [
        DocumentChunk(
            id=f"first-doc_{i}",
            text=f"Lorem ipsum {i}",
            metadata=DocumentChunkMetadata(
                source=Source.email, created_at="2023-03-05", document_id="first-doc"
            ),
            embedding=create_embedding(i, 5),
        )
        for i in range(3)
    ]
    second_doc_chunks = [
        DocumentChunk(
            id=f"second-doc_{i}",
            text=f"Dolor sit amet {i}",
            metadata=DocumentChunkMetadata(
                created_at="2023-03-04", document_id="second-doc"
            ),
            embedding=create_embedding(i + len(first_doc_chunks), 5),
        )
        for i in range(2)
    ]
    return {
        "first-doc": first_doc_chunks,
        "second-doc": second_doc_chunks,
    }


@pytest.mark.asyncio
async def test_datastore_creates_payload_indexes(
    qdrant_datastore,
    client,
):
    collection_info = client.get_collection(collection_name="documents")

    assert 2 == len(collection_info.payload_schema)
    assert "created_at" in collection_info.payload_schema
    created_at = collection_info.payload_schema["created_at"]
    assert PayloadSchemaType.INTEGER == created_at.data_type
    assert "metadata.document_id" in collection_info.payload_schema
    document_id = collection_info.payload_schema["metadata.document_id"]
    assert PayloadSchemaType.KEYWORD == document_id.data_type


@pytest.mark.asyncio
async def test_upsert_creates_all_points(
    qdrant_datastore,
    client,
    document_chunks,
):
    document_ids = await qdrant_datastore._upsert(document_chunks)

    assert 2 == len(document_ids)
    assert 5 == client.count(collection_name="documents").count


@pytest.mark.asyncio
async def test_upsert_does_not_remove_existing_documents_but_store_new(
    qdrant_datastore,
    client,
    initial_document_chunks,
    document_chunks,
):
    """
    This test ensures calling ._upsert no longer removes the existing document chunks,
    as they are currently removed in the .upsert method directly.
    """
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(initial_document_chunks)

    await qdrant_datastore._upsert(document_chunks)

    assert 8 == client.count(collection_name="documents").count


@pytest.mark.asyncio
async def test_query_returns_all_on_single_query(qdrant_datastore, document_chunks):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    query = QueryWithEmbedding(
        query="lorem",
        top_k=5,
        embedding=[0.5, 0.5, 0.5, 0.5, 0.5],
    )
    query_results = await qdrant_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert "lorem" == query_results[0].query
    assert 5 == len(query_results[0].results)


@pytest.mark.asyncio
async def test_query_returns_closest_entry(qdrant_datastore, document_chunks):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    query = QueryWithEmbedding(
        query="ipsum",
        top_k=1,
        embedding=[0.0, 0.0, 0.5, 0.0, 0.0],
    )
    query_results = await qdrant_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert "ipsum" == query_results[0].query
    assert 1 == len(query_results[0].results)
    first_document_chunk = query_results[0].results[0]
    assert 0.0 <= first_document_chunk.score <= 1.0
    assert Source.email == first_document_chunk.metadata.source
    assert "2023-03-05" == first_document_chunk.metadata.created_at
    assert "first-doc" == first_document_chunk.metadata.document_id


@pytest.mark.asyncio
async def test_query_filter_by_document_id_returns_this_document_chunks(
    qdrant_datastore, document_chunks
):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    first_query = QueryWithEmbedding(
        query="dolor",
        filter=DocumentMetadataFilter(document_id="first-doc"),
        top_k=5,
        embedding=[0.0, 0.0, 0.5, 0.0, 0.0],
    )
    second_query = QueryWithEmbedding(
        query="dolor",
        filter=DocumentMetadataFilter(document_id="second-doc"),
        top_k=5,
        embedding=[0.0, 0.0, 0.5, 0.0, 0.0],
    )
    query_results = await qdrant_datastore._query(queries=[first_query, second_query])

    assert 2 == len(query_results)
    assert "dolor" == query_results[0].query
    assert "dolor" == query_results[1].query
    assert 3 == len(query_results[0].results)
    assert 2 == len(query_results[1].results)


@pytest.mark.asyncio
@pytest.mark.parametrize("start_date", ["2023-03-05T00:00:00", "2023-03-05"])
async def test_query_start_date_converts_datestring(
    qdrant_datastore,
    document_chunks,
    start_date,
):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    query = QueryWithEmbedding(
        query="sit amet",
        filter=DocumentMetadataFilter(start_date=start_date),
        top_k=5,
        embedding=[0.0, 0.0, 0.5, 0.0, 0.0],
    )
    query_results = await qdrant_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 3 == len(query_results[0].results)


@pytest.mark.asyncio
@pytest.mark.parametrize("end_date", ["2023-03-04T00:00:00", "2023-03-04"])
async def test_query_end_date_converts_datestring(
    qdrant_datastore,
    document_chunks,
    end_date,
):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    query = QueryWithEmbedding(
        query="sit amet",
        filter=DocumentMetadataFilter(end_date=end_date),
        top_k=5,
        embedding=[0.0, 0.0, 0.5, 0.0, 0.0],
    )
    query_results = await qdrant_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 2 == len(query_results[0].results)


@pytest.mark.asyncio
async def test_delete_removes_by_ids(
    qdrant_datastore,
    client,
    document_chunks,
):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    await qdrant_datastore.delete(ids=["first-doc"])

    assert 2 == client.count(collection_name="documents").count


@pytest.mark.asyncio
async def test_delete_removes_by_document_id_filter(
    qdrant_datastore,
    client,
    document_chunks,
):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    await qdrant_datastore.delete(
        filter=DocumentMetadataFilter(document_id="first-doc")
    )

    assert 2 == client.count(collection_name="documents").count


@pytest.mark.asyncio
async def test_delete_removes_all(
    qdrant_datastore,
    client,
    document_chunks,
):
    # Fill the database with document chunks before running the actual test
    await qdrant_datastore._upsert(document_chunks)

    await qdrant_datastore.delete(delete_all=True)

    assert 0 == client.count(collection_name="documents").count
