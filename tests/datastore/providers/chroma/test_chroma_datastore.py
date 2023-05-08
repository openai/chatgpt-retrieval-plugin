from enum import Enum
from typing import Dict, List
import pytest
import random

from datastore.providers.chroma_datastore import ChromaDataStore
from models.models import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadata,
    DocumentMetadataFilter,
    Query,
    QueryWithEmbedding,
    Source,
)

PERSISTENCE_DIR = "chroma_datastore"
COLLECTION_NAME = "documents"


def ephemeral_chroma_datastore() -> ChromaDataStore:
    # Initalize an ephemeral in-memory ChromaDB instance
    return ChromaDataStore(
        collection_name=COLLECTION_NAME, in_memory=True, persistence_dir=None
    )


def persisted_chroma_datastore() -> ChromaDataStore:
    # Initialize an in-memory ChromaDB instance with persistence
    return ChromaDataStore(
        collection_name=COLLECTION_NAME, in_memory=True, persistence_dir=PERSISTENCE_DIR
    )


def get_chroma_datastore(client_fixtures: str) -> ChromaDataStore:
    if client_fixtures == "ephemeral":
        return ephemeral_chroma_datastore()
    elif client_fixtures == "persisted":
        return persisted_chroma_datastore()


client_types = ["ephemeral", "persisted"]

# Seed for deterministic testing
random.seed(0)


def create_embedding(dim: int) -> List[float]:
    return [random.random() for _ in range(dim)]


# Data fixtures
TEST_EMBEDDING_DIM = 5
N_TEST_CHUNKS = 5


@pytest.fixture
def initial_document_chunks() -> Dict[str, List[DocumentChunk]]:
    first_doc_chunks = [
        DocumentChunk(
            id=f"first-doc-{i}",
            text=f"Lorem ipsum {i}",
            metadata=DocumentChunkMetadata(),
            embedding=create_embedding(TEST_EMBEDDING_DIM),
        )
        for i in range(N_TEST_CHUNKS)
    ]
    return {
        "first-doc": first_doc_chunks,
    }


@pytest.fixture
def document_chunks(initial_document_chunks) -> Dict[str, List[DocumentChunk]]:
    doc_chunks = initial_document_chunks

    for k, v in doc_chunks.items():
        for chunk in v:
            chunk.metadata = DocumentChunkMetadata(
                source=Source.email, created_at="2023-04-03", document_id="first-doc"
            )
            chunk.embedding = create_embedding(TEST_EMBEDDING_DIM)

    doc_chunks["second_doc"] = [
        DocumentChunk(
            id=f"second-doc-{i}",
            text=f"Dolor sit amet {i}",
            metadata=DocumentChunkMetadata(
                created_at="2023-04-04", document_id="second-doc"
            ),
            embedding=create_embedding(TEST_EMBEDDING_DIM),
        )
        for i in range(N_TEST_CHUNKS)
    ]

    return doc_chunks


@pytest.mark.asyncio
@pytest.mark.parametrize("client_type", client_types)
async def test_add_chunks(
    client_type: str, document_chunks: Dict[str, List[DocumentChunk]]
):
    datastore = get_chroma_datastore(client_type)

    await datastore.delete(delete_all=True)
    assert datastore._collection.count() == 0

    print(document_chunks)

    assert await datastore._upsert(document_chunks) == list(document_chunks.keys())
    assert datastore._collection.count() == sum(
        len(v) for v in document_chunks.values()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("client_type", client_types)
async def test_upsert(
    client_type: str,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
    document_chunks: Dict[str, List[DocumentChunk]],
):
    datastore = get_chroma_datastore(client_type)

    await datastore.delete(delete_all=True)

    assert await datastore._upsert(initial_document_chunks) == list(
        initial_document_chunks.keys()
    )
    assert datastore._collection.count() == sum(
        len(v) for v in initial_document_chunks.values()
    )

    assert await datastore._upsert(document_chunks) == list(document_chunks.keys())
    assert datastore._collection.count() == sum(
        len(v) for v in document_chunks.values()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("client_type", client_types)
async def test_add_and_query_all(client_type, document_chunks):
    datastore = get_chroma_datastore(client_type)

    await datastore.delete(delete_all=True)

    await datastore._upsert(document_chunks) == list(document_chunks.keys())

    query = QueryWithEmbedding(
        query="",
        embedding=create_embedding(TEST_EMBEDDING_DIM),
        top_k=10,
    )
    query_results = await datastore._query(queries=[query])
    assert 1 == len(query_results)
    assert 10 == len(query_results[0].results)


@pytest.mark.asyncio
@pytest.mark.parametrize("client_type", client_types)
async def test_query_accuracy(client_type, document_chunks):
    for k, v in document_chunks.items():
        for chunk in v:
            print(f"id: {chunk.id} emb: {chunk.embedding}")

    def add_noise_to_embedding(embedding: List[float], eps: float = 0) -> List[float]:
        return [x + eps * (1.0 - 2 * random.random()) for x in embedding]

    datastore = get_chroma_datastore(client_type)

    await datastore.delete(delete_all=True)

    print(datastore._collection.get(include=["embeddings"]))

    res = await datastore._upsert(document_chunks)

    res = datastore._collection.get(include=["embeddings"])
    for id, emb in zip(res["ids"], res["embeddings"]):
        print(f"id: {id} emb: {emb}")

    for k, v in document_chunks.items():
        for chunk in v:
            print(f"chunk: {chunk}")
            query = QueryWithEmbedding(
                query="",
                embedding=add_noise_to_embedding(chunk.embedding),
                top_k=1,
            )
            query_results = await datastore._query(queries=[query])
            print(query_results)
            assert query_results[0].results[0].id == chunk.id


@pytest.mark.asyncio
async def test_query_filter(chroma_datastore, document_chunk_one):
    await chroma_datastore.delete(delete_all=True)
    res = await chroma_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    query = QueryWithEmbedding(
        query="lorem",
        top_k=1,
        embedding=[0] * OUTPUT_DIM,
        filter=DocumentMetadataFilter(
            start_date="2000-01-03T16:39:57-08:00", end_date="2010-01-03T16:39:57-08:00"
        ),
    )
    query_results = await chroma_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert 0 != query_results[0].results[0].score
    assert "def_456" == query_results[0].results[0].id


@pytest.mark.asyncio
async def test_delete_with_date_filter(chroma_datastore, document_chunk_one):
    await chroma_datastore.delete(delete_all=True)
    res = await chroma_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    await chroma_datastore.delete(
        filter=DocumentMetadataFilter(
            end_date="2009-01-03T16:39:57-08:00",
        )
    )

    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=[0] * OUTPUT_DIM,
    )
    query_results = await chroma_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 1 == len(query_results[0].results)
    assert "ghi_789" == query_results[0].results[0].id


@pytest.mark.asyncio
async def test_delete_with_source_filter(chroma_datastore, document_chunk_one):
    await chroma_datastore.delete(delete_all=True)
    res = await chroma_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    await chroma_datastore.delete(
        filter=DocumentMetadataFilter(
            source=Source.email,
        )
    )

    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=[0] * OUTPUT_DIM,
    )
    query_results = await chroma_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 2 == len(query_results[0].results)
    assert "def_456" == query_results[0].results[0].id


@pytest.mark.asyncio
async def test_delete_with_document_id_filter(chroma_datastore, document_chunk_one):
    await chroma_datastore.delete(delete_all=True)
    res = await chroma_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    await chroma_datastore.delete(
        filter=DocumentMetadataFilter(
            document_id=res[0],
        )
    )
    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=[0] * OUTPUT_DIM,
    )
    query_results = await chroma_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 0 == len(query_results[0].results)


@pytest.mark.asyncio
async def test_delete_with_document_id(chroma_datastore, document_chunk_one):
    await chroma_datastore.delete(delete_all=True)
    res = await chroma_datastore._upsert(document_chunk_one)
    assert res == list(document_chunk_one.keys())
    await chroma_datastore.delete([res[0]])

    query = QueryWithEmbedding(
        query="lorem",
        top_k=9,
        embedding=[0] * OUTPUT_DIM,
    )
    query_results = await chroma_datastore._query(queries=[query])

    assert 1 == len(query_results)
    assert 0 == len(query_results[0].results)
