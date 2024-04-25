import pytest
import os
import time
from typing import Union
from azure.search.documents.indexes import SearchIndexClient
from models.models import (
    DocumentMetadataFilter,
    Query,
    Source,
    Document,
    DocumentMetadata,
)

AZURESEARCH_TEST_INDEX = "testindex"
os.environ["AZURESEARCH_INDEX"] = AZURESEARCH_TEST_INDEX
if os.environ.get("AZURESEARCH_SERVICE") == None:
    os.environ[
        "AZURESEARCH_SERVICE"
    ] = "invalid service name"  # Will fail anyway if not set to a real service, but allows tests to be discovered

import datastore.providers.azuresearch_datastore
from datastore.providers.azuresearch_datastore import AzureSearchDataStore


@pytest.fixture(scope="module")
def azuresearch_mgmt_client():
    service = os.environ["AZURESEARCH_SERVICE"]
    return SearchIndexClient(
        endpoint=f"https://{service}.search.windows.net",
        credential=AzureSearchDataStore._create_credentials(False),
    )


def test_translate_filter():
    assert AzureSearchDataStore._translate_filter(DocumentMetadataFilter()) == None

    for field in ["document_id", "source", "source_id", "author"]:
        value = Source.file if field == "source" else f"test_{field}"
        needs_escaping_value = None if field == "source" else f"test'_{field}"
        assert (
            AzureSearchDataStore._translate_filter(
                DocumentMetadataFilter(**{field: value})
            )
            == f"{field} eq '{value}'"
        )
        if needs_escaping_value != None:
            assert (
                AzureSearchDataStore._translate_filter(
                    DocumentMetadataFilter(**{field: needs_escaping_value})
                )
                == f"{field} eq 'test''_{field}'"
            )

    assert (
        AzureSearchDataStore._translate_filter(
            DocumentMetadataFilter(
                document_id="test_document_id",
                source=Source.file,
                source_id="test_source_id",
                author="test_author",
            )
        )
        == "document_id eq 'test_document_id' and source eq 'file' and source_id eq 'test_source_id' and author eq 'test_author'"
    )

    with pytest.raises(ValueError):
        assert AzureSearchDataStore._translate_filter(
            DocumentMetadataFilter(start_date="2023-01-01")
        )
    with pytest.raises(ValueError):
        assert AzureSearchDataStore._translate_filter(
            DocumentMetadataFilter(end_date="2023-01-01")
        )

    assert (
        AzureSearchDataStore._translate_filter(
            DocumentMetadataFilter(
                start_date="2023-01-01T00:00:00Z",
                end_date="2023-01-02T00:00:00Z",
                document_id="test_document_id",
            )
        )
        == "document_id eq 'test_document_id' and created_at ge 2023-01-01T00:00:00Z and created_at le 2023-01-02T00:00:00Z"
    )


@pytest.mark.asyncio
async def test_lifecycle_hybrid(azuresearch_mgmt_client: SearchIndexClient):
    datastore.providers.azuresearch_datastore.AZURESEARCH_DISABLE_HYBRID = None
    datastore.providers.azuresearch_datastore.AZURESEARCH_SEMANTIC_CONFIG = None
    await lifecycle(azuresearch_mgmt_client)


@pytest.mark.asyncio
async def test_lifecycle_vectors_only(azuresearch_mgmt_client: SearchIndexClient):
    datastore.providers.azuresearch_datastore.AZURESEARCH_DISABLE_HYBRID = "1"
    datastore.providers.azuresearch_datastore.AZURESEARCH_SEMANTIC_CONFIG = None
    await lifecycle(azuresearch_mgmt_client)


@pytest.mark.asyncio
async def test_lifecycle_semantic(azuresearch_mgmt_client: SearchIndexClient):
    datastore.providers.azuresearch_datastore.AZURESEARCH_DISABLE_HYBRID = None
    datastore.providers.azuresearch_datastore.AZURESEARCH_SEMANTIC_CONFIG = (
        "testsemconfig"
    )
    await lifecycle(azuresearch_mgmt_client)


async def lifecycle(azuresearch_mgmt_client: SearchIndexClient):
    if AZURESEARCH_TEST_INDEX in azuresearch_mgmt_client.list_index_names():
        azuresearch_mgmt_client.delete_index(AZURESEARCH_TEST_INDEX)
    assert AZURESEARCH_TEST_INDEX not in azuresearch_mgmt_client.list_index_names()
    try:
        store = AzureSearchDataStore()
        index = azuresearch_mgmt_client.get_index(AZURESEARCH_TEST_INDEX)
        assert index is not None

        result = await store.upsert(
            [
                Document(
                    id="test_id_1",
                    text="test text",
                    metadata=DocumentMetadata(
                        source=Source.file,
                        source_id="test_source_id",
                        author="test_author",
                        created_at="2023-01-01T00:00:00Z",
                        url="http://some-test-url/path",
                    ),
                ),
                Document(
                    id="test_id_2+",
                    text="different",
                    metadata=DocumentMetadata(
                        source=Source.file,
                        source_id="test_source_id",
                        author="test_author",
                        created_at="2023-01-01T00:00:00Z",
                        url="http://some-test-url/path",
                    ),
                ),
            ]
        )
        assert (
            len(result) == 2 and result[0] == "test_id_1" and result[1] == "test_id_2+"
        )

        # query in a loop in case we need to retry since documents aren't searchable synchronosuly after updates
        for _ in range(4):
            time.sleep(0.25)
            result = await store.query([Query(query="text")])
            if len(result) > 0 and len(result[0].results) > 0:
                break
        assert len(result) == 1 and len(result[0].results) == 2
        assert (
            result[0].results[0].metadata.document_id == "test_id_1"
            and result[0].results[1].metadata.document_id == "test_id_2+"
        )

        result = await store.query(
            [
                Query(
                    query="text",
                    filter=DocumentMetadataFilter(source_id="test_source_id"),
                )
            ]
        )
        assert len(result) == 1 and len(result[0].results) == 2
        assert (
            result[0].results[0].metadata.document_id == "test_id_1"
            and result[0].results[1].metadata.document_id == "test_id_2+"
        )

        result = await store.query(
            [
                Query(
                    query="text",
                    filter=DocumentMetadataFilter(source_id="nonexisting_id"),
                )
            ]
        )
        assert len(result) == 1 and len(result[0].results) == 0

        result = await store.query(
            [
                Query(
                    query="text",
                    filter=DocumentMetadataFilter(start_date="2023-01-02T00:00:00Z"),
                )
            ]
        )
        assert len(result) == 1 and len(result[0].results) == 0

        result = await store.query(
            [
                Query(
                    query="text",
                    filter=DocumentMetadataFilter(start_date="2023-01-01T00:00:00Z"),
                )
            ]
        )
        assert len(result) == 1 and len(result[0].results) == 2
        assert (
            result[0].results[0].metadata.document_id == "test_id_1"
            and result[0].results[1].metadata.document_id == "test_id_2+"
        )

        result = await store.query(
            [
                Query(
                    query="text",
                    filter=DocumentMetadataFilter(end_date="2022-12-31T00:00:00Z"),
                )
            ]
        )
        assert len(result) == 1 and len(result[0].results) == 0

        result = await store.query(
            [
                Query(
                    query="text",
                    filter=DocumentMetadataFilter(end_date="2023-01-02T00:00:00Z"),
                )
            ]
        )
        assert len(result) == 1 and len(result[0].results) == 2
        assert (
            result[0].results[0].metadata.document_id == "test_id_1"
            and result[0].results[1].metadata.document_id == "test_id_2+"
        )

        # query in a loop in case we need to retry since documents aren't searchable synchronosuly after updates
        assert await store.delete(["test_id_1", "test_id_2+"])
        for _ in range(4):
            time.sleep(0.25)
            result = await store.query([Query(query="text")])
            if len(result) > 0 and len(result[0].results) == 0:
                break
        assert len(result) == 1 and len(result[0].results) == 0
    finally:
        azuresearch_mgmt_client.delete_index(AZURESEARCH_TEST_INDEX)
