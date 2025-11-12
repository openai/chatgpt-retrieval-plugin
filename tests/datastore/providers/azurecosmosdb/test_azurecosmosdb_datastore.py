import pytest
from typing import Dict, List
from dotenv import dotenv_values

from datastore.datastore import DataStore
from datastore.providers.azurecosmosdb_datastore import AzureCosmosDBDataStore
from models.models import (
    DocumentChunk,
    DocumentChunkMetadata,
    QueryWithEmbedding,
)
import os

num_lists = 1
similarity = "COS"

EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", 256))


def create_embedding(non_zero_pos: int) -> List[float]:
    # create a vector with a single non-zero value of dimension EMBEDDING_DIMENSION
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[non_zero_pos - 1] = 1.0
    return vector


@pytest.fixture
def azure_cosmos_db_settings_from_dot_env() -> dict:
    """
    Reads the Azure CosmosDB environment variables for the .env file.

    Returns:
        dict: The Azure CosmosDB environment variables
    """
    config = dotenv_values(".env")
    env_variables = {
        "DATASTORE": "azurecosmosdb",
        "AZCOSMOS_API": config.get(
            ("AZCOSMOS_API")
        ),  # Right now CosmosDB only supports vector search in Mongo vCore.
        "AZCOSMOS_CONNSTR": config.get("AZCOSMOS_CONNSTR"),
        "AZCOSMOS_DATABASE_NAME": config.get("AZCOSMOS_DATABASE_NAME"),
        "AZCOSMOS_CONTAINER_NAME": config.get("AZCOSMOS_CONTAINER_NAME"),
    }

    return env_variables


@pytest.fixture
def initial_document_chunks() -> Dict[str, List[DocumentChunk]]:
    first_doc_chunks = [
        DocumentChunk(
            id=f"first-doc-{i}",
            text=f"Lorem ipsum {i}",
            metadata=DocumentChunkMetadata(),
            embedding=create_embedding(i),
        )
        for i in range(4, 7)
    ]
    return {
        "first-doc": first_doc_chunks,
    }


@pytest.fixture
def queries() -> List[QueryWithEmbedding]:
    queries = [
        QueryWithEmbedding(
            query="Query 1",
            top_k=1,
            embedding=create_embedding(4),
        ),
        QueryWithEmbedding(
            query="Query 2",
            top_k=2,
            embedding=create_embedding(5),
        ),
    ]
    return queries


@pytest.fixture
async def azurecosmosdb_datastore() -> DataStore:
    return await AzureCosmosDBDataStore.create(
        num_lists=num_lists, similarity=similarity
    )


@pytest.mark.asyncio
async def test_upsert(
    azurecosmosdb_datastore: AzureCosmosDBDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
) -> None:
    """Test basic upsert."""
    doc_ids = await azurecosmosdb_datastore._upsert(initial_document_chunks)
    assert doc_ids == [
        f"doc:{doc_id}:chunk:{chunk.id}"
        for doc_id, chunk_list in initial_document_chunks.items()
        for chunk in chunk_list
    ]


@pytest.mark.asyncio
async def test_query(
    azurecosmosdb_datastore: AzureCosmosDBDataStore,
    initial_document_chunks: Dict[str, List[DocumentChunk]],
    queries: List[QueryWithEmbedding],
) -> None:
    """Test basic query."""
    await azurecosmosdb_datastore.delete(delete_all=True)
    # insert to prepare for the test
    await azurecosmosdb_datastore._upsert(initial_document_chunks)

    query_results = await azurecosmosdb_datastore._query(queries)
    assert len(query_results) == len(queries)

    query_0_results = query_results[0].results
    query_1_results = query_results[1].results

    assert len(query_0_results) == 1
    assert len(query_1_results) == 2

    # NOTE: this is the correct behavior
    assert query_0_results[0].id == "doc:first-doc:chunk:first-doc-4"
    assert query_1_results[0].id == "doc:first-doc:chunk:first-doc-5"
    assert query_1_results[1].id == "doc:first-doc:chunk:first-doc-4"


@pytest.mark.asyncio
async def test_delete(azurecosmosdb_datastore: AzureCosmosDBDataStore) -> None:
    await azurecosmosdb_datastore.delete(delete_all=True)
    chunk1 = DocumentChunk(
        id="deleteChunk1",
        text="delete text 1",
        embedding=[1] * EMBEDDING_DIMENSION,
        metadata=DocumentChunkMetadata(),
    )
    chunk2 = DocumentChunk(
        id="deleteChunk2",
        text="delete text 2",
        embedding=[1] * EMBEDDING_DIMENSION,
        metadata=DocumentChunkMetadata(),
    )
    # insert to prepare for test
    await azurecosmosdb_datastore._upsert(
        {"deleteDoc1": [chunk1], "deleteDoc2": [chunk2]}
    )

    query_embedding = [1] * EMBEDDING_DIMENSION
    query = QueryWithEmbedding(
        query="Query for delete",
        embedding=query_embedding,
    )
    results = await azurecosmosdb_datastore._query([query])

    assert len(results[0].results) == 2
    assert results[0].results[0].id == "doc:deleteDoc1:chunk:deleteChunk1"
    assert results[0].results[1].id == "doc:deleteDoc2:chunk:deleteChunk2"

    await azurecosmosdb_datastore.delete(ids=["doc:deleteDoc1:chunk:deleteChunk1"])
    results_after_delete = await azurecosmosdb_datastore._query([query])

    assert len(results_after_delete[0].results) == 1
    assert results_after_delete[0].results[0].id == "doc:deleteDoc2:chunk:deleteChunk2"


@pytest.mark.asynio
async def test_delete_all(azurecosmosdb_datastore: AzureCosmosDBDataStore) -> None:
    await azurecosmosdb_datastore.delete(delete_all=True)
    chunk = DocumentChunk(
        id="deleteChunk",
        text="delete text",
        embedding=[1] * EMBEDDING_DIMENSION,
        metadata=DocumentChunkMetadata(),
    )
    await azurecosmosdb_datastore._upsert({"deleteDoc": [chunk]})

    query_embedding = [1] * EMBEDDING_DIMENSION
    query = QueryWithEmbedding(
        query="delete query",
        embedding=query_embedding,
        top_k=1,
    )
    results = await azurecosmosdb_datastore._query([query])

    assert len(results) == 1
    assert len(results[0].results) == 1
    assert results[0].results[0].id == "doc:deleteDoc:chunk:deleteChunk"

    await azurecosmosdb_datastore.delete(delete_all=True)
    results_after_delete = await azurecosmosdb_datastore._query([query])

    assert len(results_after_delete[0].results) == 0
