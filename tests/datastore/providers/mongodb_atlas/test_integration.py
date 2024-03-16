"""Integration Tests of ChatGPT Retrieval Plugin
with MongoDB Atlas Vector Datastore and OPENAI Embedding model.

As described in docs/providers/mongodb/setup.md including,
to run this, one must have both a running MongoDB Atlas Cluster,
and a running ChatGPT Retrieval Plugin service.
One must also provide a valid OPENAI_API_KEY.
"""

import os
import openai
from pymongo import MongoClient
import pytest
import requests
from requests.adapters import HTTPAdapter, Retry
from time import sleep


def test_required_vars() -> None:
    """Confirm that the environment has all it needs"""
    required_vars = {'BEARER_TOKEN', 'OPENAI_API_KEY', 'DATASTORE', 'EMBEDDING_DIMENSION', 'EMBEDDING_MODEL',
                     'MONGODB_COLLECTION', 'MONGODB_DATABASE', 'MONGODB_INDEX', 'MONGODB_URI'}
    assert os.environ["DATASTORE"] == 'mongodb'
    missing = required_vars - set(os.environ)
    assert len(missing) == 0


def test_mongodb_connection() -> None:
    """Start a synchronous MongoClient.
    Send a ping to confirm a successful connection.
    """
    client = MongoClient(os.environ["MONGODB_URI"])
    assert client.admin.command('ping')['ok']


def test_openai_connection() -> None:
    """Check that we can call OpenAI Embedding models"""
    openai.api_key = os.environ["OPENAI_API_KEY"]
    models = openai.Model.list()
    model_names = [model["id"] for model in models['data']]
    for model_name in model_names:
        try:
            response = openai.Embedding.create(input=["Some input text"], model=model_name)
            assert len(response['data'][0]['embedding']) >= int(os.environ['EMBEDDING_DIMENSION'])
        except:
            pass  # Not all models are for text embedding.


@pytest.fixture(scope="session")
def endpoint_url() -> str:
    """URL to running Retrieval Plugin Service
    See README.md `poetry run start`
    """
    return 'http://0.0.0.0:8000'


@pytest.fixture(scope="session")
def headers() -> dict:
    """JSON Request headers"""
    return {"Authorization": f"Bearer {os.environ['BEARER_TOKEN']}"}


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


@pytest.fixture(scope="session")
def delete(endpoint_url, headers) -> bool:
    """Drop documents from the collection"""
    requests.delete(url=f"{endpoint_url}/delete", headers=headers, json={"delete_all": True})
    sleep(2)  # Be conservative


@pytest.fixture(scope="session")
def upsert(delete, documents, endpoint_url, headers) -> bool:
    """ Upload documents to the datastore via plugin's REST API.

    Makes post requests that allow up to 5 retries
    """
    batch_size = 100
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    n_docs = len(documents)
    assert n_docs == 4
    for i in range(0, n_docs, batch_size):
        i_end = min(n_docs, i + batch_size)
        assert isinstance(documents[i:i_end], list)
        assert isinstance(documents[i:i_end][0], dict)
        res = session.post(
            f"{endpoint_url}/upsert",
            headers=headers,
            json={"documents": documents[i:i_end]}
        )
    sleep(2)  # At this point, the Vector Search Index is being built
    return True


def test_upsert(upsert) -> None:
    """Simply confirm that upsert fixture has run successfully"""
    assert upsert


def post_query(question: str, endpoint: str, json_headers: dict, top_k: int=2):
    """Helper function. Posts a query to Plugin API

    Although the plugin endpoint takes a list, we are just using one..
    """
    response = requests.post(
        f"{endpoint}/query",
        headers=json_headers,
        json={'queries': [{"query": question, "top_k": top_k}]}
    )
    assert len(response.json()) == 1
    query_result = response.json()['results'][0]
    print(f"\n\n{response.json() = }\n\n")
    query = query_result['query']
    answers = []
    scores = []
    for result in query_result['results']:
        answers.append(result['text'])
        scores.append(round(result['score'], 2))
    return dict(query=query, answers=answers, scores=scores)


def test_query(upsert, endpoint_url, headers) -> None:
    """Test queries produce reasonable results,
    now that datastore contains embedded data which has been indexed
    """
    question = "What did the fox jump over?"
    n_results = 2
    got_response = False
    while got_response is False:
        response = post_query(question, endpoint_url, headers, top_k=n_results)
        assert isinstance(response, dict)
        if len(response["scores"]) == n_results:
            got_response = True
            assert len(response["scores"]) == n_results
            assert 0.8 < response["scores"][0] < 0.9
            assert response["answers"][0] == "The quick brown fox jumped over the slimy green toad."

    question = "What are red frogs?"
    response = post_query(question, endpoint_url, headers, top_k=n_results)
    assert len(response["scores"]) == n_results
    assert response["answers"][0] == "Green toads are basically red frogs."
