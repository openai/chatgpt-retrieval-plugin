import shutil
from typing import Dict, List
import pytest
import random

from datastore.providers.chroma_datastore import ChromaDataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentMetadataFilter,
    QueryWithEmbedding,
    Source,
)

TEST_PERSISTENCE_DIR = "chroma_test_datastore"
COLLECTION_NAME = "documents"


def ephemeral_chroma_datastore() -> ChromaDataStore:
    # Initialize an ephemeral in-memory ChromaDB instance
    return ChromaDataStore(
        collection_name=COLLECTION_NAME, in_memory=True, persistence_dir=None
    )


def persisted_chroma_datastore() -> ChromaDataStore:
    # Initialize an in-memory ChromaDB instance with persistence
    return ChromaDataStore(
        collection_name=COLLECTION_NAME,
        in_memory=True,
        persistence_dir=TEST_PERSISTENCE_DIR,
    )


def get_chroma_datastore() -> ChromaDataStore:
    yield ephemeral_chroma_datastore()
    yield persisted_chroma_datastore()
    # Delete the persistence directory after the test


@pytest.fixture(autouse=True)
def cleanup():
    yield
    shutil.rmtree(TEST_PERSISTENCE_DIR, ignore_errors=True)


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

    doc_chunks["second-doc"] = [
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
async def test_add_chunks(document_chunks: Dict[str, List[DocumentChunk]]):
    for datastore in get_chroma_datastore():
        await datastore.delete(delete_all=True)
        assert datastore._collection.count() == 0

        print(document_chunks)

        assert await datastore._upsert(document_chunks) == list(document_chunks.keys())
        assert datastore._collection.count() == sum(
            len(v) for v in document_chunks.values()
        )


@pytest.mark.asyncio
async def test_upsert(
    initial_document_chunks: Dict[str, List[DocumentChunk]],
    document_chunks: Dict[str, List[DocumentChunk]],
):
    for datastore in get_chroma_datastore():
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
async def test_add_and_query_all(document_chunks):
    for datastore in get_chroma_datastore():
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
async def test_query_accuracy(document_chunks):
    for _, v in document_chunks.items():
        for chunk in v:
            print(f"id: {chunk.id} emb: {chunk.embedding}")

    def add_noise_to_embedding(embedding: List[float], eps: float = 0) -> List[float]:
        return [x + eps * (1.0 - 2 * random.random()) for x in embedding]

    for datastore in get_chroma_datastore():
        await datastore.delete(delete_all=True)

        print(datastore._collection.get(include=["embeddings"]))

        res = await datastore._upsert(document_chunks)

        res = datastore._collection.get(include=["embeddings"])
        for id, emb in zip(res["ids"], res["embeddings"]):
            print(f"id: {id} emb: {emb}")

        for _, v in document_chunks.items():
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
async def test_query_filter_by_id(document_chunks):
    for datastore in get_chroma_datastore():
        await datastore.delete(delete_all=True)

        await datastore._upsert(document_chunks)

        for doc_id, chunks in document_chunks.items():
            query = QueryWithEmbedding(
                query="",
                embedding=chunks[0].embedding,
                top_k=N_TEST_CHUNKS,
                filter=DocumentMetadataFilter(document_id=doc_id),
            )
            query_results = await datastore._query(queries=[query])
            # Assert that all document chunks are returned
            assert len(query_results[0].results) == len(chunks)
            assert all(
                [
                    result.id in [chunk.id for chunk in chunks]
                    for result in query_results[0].results
                ]
            )


@pytest.mark.asyncio
async def test_query_filter_by_date(document_chunks):
    for datastore in get_chroma_datastore():
        await datastore.delete(delete_all=True)

        await datastore._upsert(document_chunks)

        # Filter by dates for only the first document
        query = QueryWithEmbedding(
            query="",
            embedding=document_chunks["first-doc"][0].embedding,
            top_k=N_TEST_CHUNKS,
            filter=DocumentMetadataFilter(
                start_date="2023-04-03", end_date="2023-04-03"
            ),
        )

        query_results = await datastore._query(queries=[query])

        # Assert that only the first document is returned
        assert len(query_results[0].results) == len(document_chunks["first-doc"])
        assert all(
            [
                result.id in [chunk.id for chunk in document_chunks["first-doc"]]
                for result in query_results[0].results
            ]
        )

        # Filter for the entire date span
        query = QueryWithEmbedding(
            query="",
            embedding=document_chunks["first-doc"][0].embedding,
            top_k=N_TEST_CHUNKS * len(document_chunks),
            filter=DocumentMetadataFilter(
                start_date="2023-04-03", end_date="2023-04-04"
            ),
        )

        query_results = await datastore._query(queries=[query])

        # Assert that both documents are returned
        assert len(query_results[0].results) == len(document_chunks["first-doc"]) + len(
            document_chunks["second-doc"]
        )
        assert all(
            [
                result.id
                in [chunk.id for chunk in document_chunks["first-doc"]]
                + [chunk.id for chunk in document_chunks["second-doc"]]
                for result in query_results[0].results
            ]
        )


@pytest.mark.asyncio
async def test_delete_by_id(document_chunks):
    for datastore in get_chroma_datastore():
        await datastore.delete(delete_all=True)

        await datastore._upsert(document_chunks)

        # Delete the first document
        await datastore.delete(ids=["first-doc"])

        # Assert that the first document is deleted
        query = QueryWithEmbedding(
            query="",
            embedding=document_chunks["first-doc"][0].embedding,
            top_k=N_TEST_CHUNKS,
        )
        query_results = await datastore._query(queries=[query])

        # Assert that only the second document is still there
        query_results = await datastore._query(queries=[query])
        assert len(query_results[0].results) == len(document_chunks["second-doc"])

        assert all(
            [
                result.id in [chunk.id for chunk in document_chunks["second-doc"]]
                for result in query_results[0].results
            ]
        )
