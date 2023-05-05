import logging
import os

import pytest
import weaviate
from _pytest.logging import LogCaptureFixture
from fastapi.testclient import TestClient
from loguru import logger
from weaviate import Client

from datastore.providers.weaviate_datastore import (
    SCHEMA,
    WeaviateDataStore,
    extract_schema_properties,
)
from models.models import DocumentMetadataFilter, Source
from server.main import app

BEARER_TOKEN = os.getenv("BEARER_TOKEN")

client = TestClient(app)
client.headers["Authorization"] = f"Bearer {BEARER_TOKEN}"


@pytest.fixture
def weaviate_client():
    host = os.getenv("WEAVIATE_HOST", "http://localhost")
    port = os.getenv("WEAVIATE_PORT", "8080")
    client = Client(f"{host}:{port}")

    yield client

    client.schema.delete_all()


@pytest.fixture
def test_db(weaviate_client, documents):
    weaviate_client.schema.delete_all()
    weaviate_client.schema.create_class(SCHEMA)

    response = client.post("/upsert", json={"documents": documents})

    if response.status_code != 200:
        raise Exception(
            f"Could not upsert to test client.\nStatus Code: {response.status_code}\nResponse:\n{response.json()}"
        )

    yield client


@pytest.fixture
def documents():
    documents = []

    authors = ["Max Mustermann", "John Doe", "Jane Doe"]
    texts = [
        "lorem ipsum dolor sit amet",
        "consectetur adipiscing elit",
        "sed do eiusmod tempor incididunt",
    ]
    ids = ["abc_123", "def_456", "ghi_789"]
    sources = ["chat", "email", "email"]
    created_at = [
        "1929-10-28T09:30:00-05:00",
        "2009-01-03T16:39:57-08:00",
        "2021-01-21T10:00:00-02:00",
    ]

    for i in range(3):
        documents.append(
            {
                "id": ids[i],
                "text": texts[i],
                "metadata": {
                    "source": sources[i],
                    "source_id": "5325",
                    "url": "http://example.com",
                    "created_at": created_at[i],
                    "author": authors[i],
                },
            }
        )

    no_metadata_doc = {
        "id": "jkl_012",
        "text": "no metadata",
    }

    documents.append(no_metadata_doc)

    partial_metadata_doc = {
        "id": "mno_345",
        "text": "partial metadata",
        "metadata": {
            "source": "file",
        },
    }

    documents.append(partial_metadata_doc)

    yield documents


@pytest.fixture
def caplog(caplog: LogCaptureFixture):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.mark.parametrize(
    "document_id", [("abc_123"), ("9a253e0b-d2df-5c2e-be6d-8e9b1f4ae345")]
)
def test_upsert(weaviate_client, document_id):
    weaviate_client.schema.delete_all()
    weaviate_client.schema.create_class(SCHEMA)

    text = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce in ipsum eget dolor malesuada fermentum at ac massa. 
    Aliquam erat volutpat. Sed eu velit est. Morbi semper quam id urna fringilla lacinia. Vivamus sit amet velit id lorem 
    pretium molestie. Nulla tincidunt sapien eu nulla consequat, a lacinia justo facilisis. Maecenas euismod urna sapien, 
    sit amet tincidunt est dapibus ac. Sed in lorem in nunc tincidunt bibendum. Nullam vel urna vitae nulla iaculis rutrum. 
    Suspendisse varius, massa a dignissim vehicula, urna ligula tincidunt orci, id fringilla velit tellus eu metus. Sed 
    vestibulum, nisl in malesuada tempor, nisi turpis facilisis nibh, nec dictum velit velit vel ex. Donec euismod, 
    leo ut sollicitudin tempor, dolor augue blandit nunc, eu lacinia ipsum turpis vitae nulla. Aenean bibendum 
    tincidunt magna in pulvinar. Sed tincidunt vel nisi ac maximus.
    """
    source = "email"
    source_id = "5325"
    url = "http://example.com"
    created_at = "2022-12-16T08:00:00+01:00"
    author = "Max Mustermann"

    documents = {
        "documents": [
            {
                "id": document_id,
                "text": text,
                "metadata": {
                    "source": source,
                    "source_id": source_id,
                    "url": url,
                    "created_at": created_at,
                    "author": author,
                },
            }
        ]
    }

    response = client.post("/upsert", json=documents)

    assert response.status_code == 200
    assert response.json() == {"ids": [document_id]}

    properties = [
        "chunk_id",
        "document_id",
        "source",
        "source_id",
        "url",
        "created_at",
        "author",
    ]

    where_filter = {
        "path": ["document_id"],
        "operator": "Equal",
        "valueString": document_id,
    }

    weaviate_doc = (
        weaviate_client.query.get("OpenAIDocument", properties)
        .with_additional("vector")
        .with_where(where_filter)
        .with_sort({"path": ["chunk_id"], "order": "asc"})
        .do()
    )

    weaviate_docs = weaviate_doc["data"]["Get"]["OpenAIDocument"]

    assert len(weaviate_docs) == 2

    for i, weaviate_doc in enumerate(weaviate_docs):
        assert weaviate_doc["chunk_id"] == f"{document_id}_{i}"

        assert weaviate_doc["document_id"] == document_id

        assert weaviate_doc["source"] == source
        assert weaviate_doc["source_id"] == source_id
        assert weaviate_doc["url"] == url
        assert weaviate_doc["created_at"] == created_at
        assert weaviate_doc["author"] == author

        assert weaviate_doc["_additional"]["vector"]


def test_upsert_no_metadata(weaviate_client):
    weaviate_client.schema.delete_all()
    weaviate_client.schema.create_class(SCHEMA)

    no_metadata_doc = {
        "id": "jkl_012",
        "text": "no metadata",
    }

    metadata_properties = [
        "source",
        "source_id",
        "url",
        "created_at",
        "author",
    ]

    response = client.post("/upsert", json={"documents": [no_metadata_doc]})

    assert response.status_code == 200

    weaviate_doc = weaviate_client.query.get("OpenAIDocument", metadata_properties).do()

    weaviate_doc = weaviate_doc["data"]["Get"]["OpenAIDocument"][0]

    for _, metadata_value in weaviate_doc.items():
        assert metadata_value is None


@pytest.mark.parametrize(
    "test_document, expected_status_code",
    [
        ({"id": "abc_123", "text": "some text"}, 200),
        ({"id": "abc_123"}, 422),
        ({"text": "some text"}, 200),
    ],
)
def test_upsert_invalid_documents(weaviate_client, test_document, expected_status_code):
    weaviate_client.schema.delete_all()
    weaviate_client.schema.create_class(SCHEMA)

    response = client.post("/upsert", json={"documents": [test_document]})

    assert response.status_code == expected_status_code


@pytest.mark.parametrize(
    "query, expected_num_results",
    [
        ({"query": "consectetur adipiscing", "top_k": 3}, 3),
        ({"query": "consectetur adipiscing elit", "filter": {"source": "email"}}, 2),
        (
            {
                "query": "sed do eiusmod tempor",
                "filter": {
                    "start_date": "2020-01-01T00:00:00Z",
                    "end_date": "2022-12-31T00:00:00Z",
                },
            },
            1,
        ),
        (
            {
                "query": "some random query",
                "filter": {"start_date": "2009-01-01T00:00:00Z"},
                "top_k": 3,
            },
            2,
        ),
        (
            {
                "query": "another random query",
                "filter": {"end_date": "1929-12-31T00:00:00Z"},
                "top_k": 3,
            },
            1,
        ),
    ],
)
def test_query(test_db, query, expected_num_results):
    queries = {"queries": [query]}

    response = client.post("/query", json=queries)
    assert response.status_code == 200

    num_docs = response.json()["results"][0]["results"]
    assert len(num_docs) == expected_num_results


def test_delete(test_db, weaviate_client, caplog):
    caplog.set_level(logging.DEBUG)

    delete_request = {"ids": ["def_456"]}

    response = client.request(method="delete", url="/delete", json=delete_request)
    assert response.status_code == 200
    assert response.json()["success"]
    assert weaviate_client.data_object.get()["totalResults"] == 4

    client.request(method="delete", url="/delete", json=delete_request)
    assert "Failed to delete" in caplog.text
    caplog.clear()

    delete_request = {"filter": {"source": "email"}}

    response = client.request(method="delete", url="/delete", json=delete_request)
    assert response.status_code == 200
    assert response.json()["success"]
    assert weaviate_client.data_object.get()["totalResults"] == 3

    client.request(method="delete", url="/delete", json=delete_request)
    assert "Failed to delete" in caplog.text

    delete_request = {"delete_all": True}

    response = client.request(method="delete", url="/delete", json=delete_request)
    assert response.status_code == 200
    assert response.json()["success"]
    assert not weaviate_client.data_object.get()["objects"]


def test_build_auth_credentials(monkeypatch):
    # Test when WEAVIATE_URL ends with weaviate.network and WEAVIATE_API_KEY is set
    with monkeypatch.context() as m:
        m.setenv("WEAVIATE_URL", "https://example.weaviate.network")
        m.setenv("WEAVIATE_API_KEY", "your_api_key")
        auth_credentials = WeaviateDataStore._build_auth_credentials()
        assert auth_credentials is not None
        assert isinstance(auth_credentials, weaviate.auth.AuthApiKey)
        assert auth_credentials.api_key == "your_api_key"

    # Test when WEAVIATE_URL ends with weaviate.network and WEAVIATE_API_KEY is not set
    with monkeypatch.context() as m:
        m.setenv("WEAVIATE_URL", "https://example.weaviate.network")
        m.delenv("WEAVIATE_API_KEY", raising=False)
        with pytest.raises(
            ValueError, match="WEAVIATE_API_KEY environment variable is not set"
        ):
            WeaviateDataStore._build_auth_credentials()

    # Test when WEAVIATE_URL does not end with weaviate.network
    with monkeypatch.context() as m:
        m.setenv("WEAVIATE_URL", "https://example.notweaviate.network")
        m.setenv("WEAVIATE_API_KEY", "your_api_key")
        auth_credentials = WeaviateDataStore._build_auth_credentials()
        assert auth_credentials is None

    # Test when WEAVIATE_URL is not set
    with monkeypatch.context() as m:
        m.delenv("WEAVIATE_URL", raising=False)
        m.setenv("WEAVIATE_API_KEY", "your_api_key")
        auth_credentials = WeaviateDataStore._build_auth_credentials()
        assert auth_credentials is None


def test_extract_schema_properties():
    class_schema = {
        "class": "Question",
        "description": "Information from a Jeopardy! question",
        "properties": [
            {
                "dataType": ["text"],
                "description": "The question",
                "name": "question",
            },
            {
                "dataType": ["text"],
                "description": "The answer",
                "name": "answer",
            },
            {
                "dataType": ["text"],
                "description": "The category",
                "name": "category",
            },
        ],
        "vectorizer": "text2vec-openai",
    }
    results = extract_schema_properties(class_schema)
    assert results == {"question", "answer", "category"}


def test_reuse_schema(weaviate_client, caplog):
    caplog.set_level(logging.DEBUG)

    weaviate_client.schema.delete_all()

    WeaviateDataStore()
    assert "Creating index" in caplog.text

    WeaviateDataStore()
    assert "Will reuse this schema" in caplog.text


def test_build_date_filters():
    filter = DocumentMetadataFilter(
        document_id=None,
        source=None,
        source_id=None,
        author=None,
        start_date="2020-01-01T00:00:00Z",
        end_date="2022-12-31T00:00:00Z",
    )
    actual_result = WeaviateDataStore.build_filters(filter)
    expected_result = {
        "operator": "And",
        "operands": [
            {
                "path": ["created_at"],
                "operator": "GreaterThanEqual",
                "valueDate": "2020-01-01T00:00:00Z",
            },
            {
                "path": ["created_at"],
                "operator": "LessThanEqual",
                "valueDate": "2022-12-31T00:00:00Z",
            },
        ],
    }

    assert actual_result == expected_result


@pytest.mark.parametrize(
    "test_input, expected_result",
    [
        ("abc_123", False),
        ("b2e4133c-c956-5684-bbf5-584e50ec3647", True),  # version 5
        ("f6179953-11d8-4ee0-9af8-e51e00dbf727", True),  # version 4
        ("16fe8165-3c08-348f-a015-a8bb31e26b5c", True),  # version 3
        ("bda85f97-be72-11ed-9291-00000000000a", False),  # version 1
    ],
)
def test_is_valid_weaviate_id(test_input, expected_result):
    actual_result = WeaviateDataStore._is_valid_weaviate_id(test_input)
    assert actual_result == expected_result


def test_upsert_same_docid(test_db, weaviate_client):
    def get_doc_by_document_id(document_id):
        properties = [
            "chunk_id",
            "document_id",
            "source",
            "source_id",
            "url",
            "created_at",
            "author",
        ]
        where_filter = {
            "path": ["document_id"],
            "operator": "Equal",
            "valueString": document_id,
        }

        results = (
            weaviate_client.query.get("OpenAIDocument", properties)
            .with_additional("id")
            .with_where(where_filter)
            .with_sort({"path": ["chunk_id"], "order": "asc"})
            .do()
        )

        return results["data"]["Get"]["OpenAIDocument"]

    def build_upsert_payload(document):
        return {"documents": [document]}

    # upsert a new document
    # this is a document that has 2 chunks and
    # the source is email
    doc_id = "abc_123"
    text = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce in ipsum eget dolor malesuada fermentum at ac massa. 
    Aliquam erat volutpat. Sed eu velit est. Morbi semper quam id urna fringilla lacinia. Vivamus sit amet velit id lorem 
    pretium molestie. Nulla tincidunt sapien eu nulla consequat, a lacinia justo facilisis. Maecenas euismod urna sapien, 
    sit amet tincidunt est dapibus ac. Sed in lorem in nunc tincidunt bibendum. Nullam vel urna vitae nulla iaculis rutrum. 
    Suspendisse varius, massa a dignissim vehicula, urna ligula tincidunt orci, id fringilla velit tellus eu metus. Sed 
    vestibulum, nisl in malesuada tempor, nisi turpis facilisis nibh, nec dictum velit velit vel ex. Donec euismod, 
    leo ut sollicitudin tempor, dolor augue blandit nunc, eu lacinia ipsum turpis vitae nulla. Aenean bibendum 
    tincidunt magna in pulvinar. Sed tincidunt vel nisi ac maximus.
    """

    document = {
        "id": doc_id,
        "text": text,
        "metadata": {"source": Source.email},
    }

    response = client.post("/upsert", json=build_upsert_payload(document))
    assert response.status_code == 200

    weaviate_doc = get_doc_by_document_id(doc_id)
    assert len(weaviate_doc) == 2
    for chunk in weaviate_doc:
        assert chunk["source"] == Source.email

    # now update the source to file
    # user still has to specify the text
    # because test is a required field
    document["metadata"]["source"] = Source.file
    response = client.post("/upsert", json=build_upsert_payload(document))
    assert response.status_code == 200

    weaviate_doc = get_doc_by_document_id(doc_id)
    assert len(weaviate_doc) == 2
    for chunk in weaviate_doc:
        assert chunk["source"] == "file"

    # now update the text so that it is only 1 chunk
    # user does not need to specify metadata
    # since it is optional
    document["text"] = "This is a short text"
    document.pop("metadata")

    response = client.post("/upsert", json=build_upsert_payload(document))
    assert response.status_code == 200
    weaviate_doc = get_doc_by_document_id(doc_id)
    assert len(weaviate_doc) == 1

    # TODO: Implement update function
    # but the source should still be file
    # but it is None right now because an
    # update function is out of scope
    assert weaviate_doc[0]["source"] is None


@pytest.mark.parametrize(
    "url, expected_result",
    [
        ("https://example.weaviate.network", True),
        ("https://example.weaviate.network/", True),
        ("https://example.weaviate.cloud", True),
        ("https://example.weaviate.cloud/", True),
        ("https://example.notweaviate.network", False),
        ("https://weaviate.network.example.com", False),
        ("https://example.weaviate.network/somepage", False),
        ("", False),
    ],
)
def test_is_wcs_domain(url, expected_result):
    assert WeaviateDataStore._is_wcs_domain(url) == expected_result
