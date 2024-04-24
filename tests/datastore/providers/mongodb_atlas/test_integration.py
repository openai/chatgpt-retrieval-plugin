"""Integration Tests of ChatGPT Retrieval Plugin
with MongoDB Atlas Vector Datastore and OPENAI Embedding model.

As described in docs/providers/mongodb/setup.md, to run this, one must
have a running MongoDB Atlas Cluster, and
provide a valid OPENAI_API_KEY.
"""

import os
from time import sleep

import openai
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pymongo import MongoClient

from server.main import app


@pytest.fixture(scope="session")
def documents():
    """ List of documents represents data to be embedded in the datastore.
    Minimum requirements fpr Documents in the /upsert endpoint's UpsertRequest.
    """
    return [
        {"text": "The quick brown fox jumped over the slimy green toad."},
        {"text": "The big brown bear jumped over the lazy dog."},
        {"text": "Toads are frogs."},
        {"text": "Green toads are basically red frogs."},
    ]


@pytest.fixture(scope="session", autouse=True)
def client():
    """TestClient makes requests to FastAPI service."""
    endpoint_url = "http://127.0.0.1:8000"
    headers = {"Authorization": f"Bearer {os.environ['BEARER_TOKEN']}"}
    with TestClient(app=app, base_url=endpoint_url, headers=headers) as client:
        yield client


@pytest.fixture(scope="session")
def delete(client) -> bool:
    """Drop existing documents from the collection"""
    response = client.request("DELETE", "/delete", json={"delete_all": True})
    sleep(2)
    return response


@pytest.fixture(scope="session")
def upsert(delete, documents, client) -> bool:
    """Upload documents to the datastore via plugin's REST API."""
    response = client.post("/upsert", json={"documents": documents})
    sleep(2)  # At this point, the Vector Search Index is being built
    return response


def test_delete(delete) -> None:
    """Simply confirm that delete fixture ran successfully"""
    assert delete.status_code == 200
    assert delete.json()['success']


def test_upsert(upsert) -> None:
    """Simply confirm that upsert fixture has run successfully"""
    assert upsert.status_code == 200
    assert len(upsert.json()['ids']) == 4


def test_query(upsert, client) -> None:  # upsert,
    """Test queries produce reasonable results,
    now that datastore contains embedded data which has been indexed
    """
    question = "What did the fox jump over?"
    n_requested = 2  # top N results per query
    got_response = False
    retries = 5
    query_result = {}
    while retries and not got_response:
        response = client.post("/query", json={'queries': [{"query": question, "top_k": n_requested}]})
        assert isinstance(response, Response)
        assert response.status_code == 200
        assert len(response.json()) == 1
        query_result = response.json()['results'][0]
        if len(query_result['results']) == n_requested:
            got_response = True
        else:
            retries -= 1
            sleep(5)

    assert got_response  # we got n_requested responses
    assert query_result['query'] == question
    answers = []
    scores = []
    for result in query_result['results']:
        answers.append(result['text'])
        scores.append(round(result['score'], 2))
    assert 0.8 < scores[0] < 0.9
    assert answers[0] == "The quick brown fox jumped over the slimy green toad."


def test_required_vars() -> None:
    """Confirm that the environment has all it needs"""
    required_vars = {'BEARER_TOKEN', 'OPENAI_API_KEY', 'DATASTORE', 'EMBEDDING_DIMENSION', 'EMBEDDING_MODEL',
                     'MONGODB_COLLECTION', 'MONGODB_DATABASE', 'MONGODB_INDEX', 'MONGODB_URI'}
    assert os.environ["DATASTORE"] == 'mongodb'
    missing = required_vars - set(os.environ)
    assert len(missing) == 0


def test_mongodb_connection() -> None:
    """Confirm that the connection to the datastore works."""
    client = MongoClient(os.environ["MONGODB_URI"])
    assert client.admin.command('ping')['ok']


def test_openai_connection() -> None:
    """Check that we can call OpenAI Embedding models."""
    openai.api_key = os.environ["OPENAI_API_KEY"]
    models = openai.Model.list()
    model_names = [model["id"] for model in models['data']]
    for model_name in model_names:
        try:
            response = openai.Embedding.create(input=["Some input text"], model=model_name)
            assert len(response['data'][0]['embedding']) >= int(os.environ['EMBEDDING_DIMENSION'])
        except:
            pass  # Not all models are for text embedding.
