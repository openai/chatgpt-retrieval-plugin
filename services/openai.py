from typing import List, Optional
import openai
import os
import json
import urllib.request
import urllib.error
from loguru import logger

from tenacity import retry, wait_random_exponential, stop_after_attempt

EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", 256))

# MiniMax configuration
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY")
MINIMAX_API_BASE = os.environ.get("MINIMAX_API_BASE", "https://api.minimax.io/v1")
MINIMAX_CHAT_MODEL = os.environ.get("MINIMAX_CHAT_MODEL", "MiniMax-M2.7")


def _get_minimax_embeddings(texts: List[str], embedding_type: str = "db") -> List[List[float]]:
    """
    Get embeddings using MiniMax's embedding API.

    MiniMax's embedding API uses a different format than OpenAI's:
    - Uses 'texts' parameter instead of 'input'
    - Requires a 'type' parameter: 'db' for document storage, 'query' for search queries
    - Returns 'vectors' instead of 'data[].embedding'

    Args:
        texts: The list of texts to embed.
        embedding_type: The type of embedding - 'db' for documents, 'query' for search queries.

    Returns:
        A list of embeddings, each of which is a list of floats.
    """
    if not MINIMAX_API_KEY:
        raise ValueError(
            "MINIMAX_API_KEY environment variable is required when using MiniMax as the embedding provider. "
            "Get your API key at https://platform.minimaxi.com/"
        )

    url = f"{MINIMAX_API_BASE}/embeddings"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": EMBEDDING_MODEL,
        "texts": texts,
        "type": embedding_type,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        raise Exception(f"MiniMax embedding API error ({e.code}): {error_body}")

    # Check for API-level errors
    base_resp = result.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise Exception(
            f"MiniMax embedding API error: {base_resp.get('status_msg', 'Unknown error')}"
        )

    vectors = result.get("vectors")
    if not vectors:
        raise Exception("MiniMax embedding API returned no vectors")

    return vectors


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
def get_embeddings(texts: List[str], embedding_type: str = "db") -> List[List[float]]:
    """
    Embed texts using the configured embedding provider.

    Supports OpenAI (default), Azure OpenAI, and MiniMax as embedding providers.
    Set the EMBEDDING_PROVIDER environment variable to choose the provider:
    - "openai" (default): Uses OpenAI's embedding models
    - "minimax": Uses MiniMax's embedding API (https://api.minimax.io/v1)

    Args:
        texts: The list of texts to embed.
        embedding_type: The type of embedding context - 'db' for document storage,
            'query' for search queries. Used by MiniMax for asymmetric embeddings;
            ignored by OpenAI.

    Returns:
        A list of embeddings, each of which is a list of floats.

    Raises:
        Exception: If the embedding API call fails.
    """
    if EMBEDDING_PROVIDER == "minimax":
        return _get_minimax_embeddings(texts, embedding_type=embedding_type)

    # OpenAI / Azure OpenAI path
    # NOTE: Azure Open AI requires deployment id
    deployment = os.environ.get("OPENAI_EMBEDDINGMODEL_DEPLOYMENTID")

    response = {}
    if deployment is None:
        response = openai.Embedding.create(input=texts, model=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMENSION)
    else:
        response = openai.Embedding.create(input=texts, deployment_id=deployment)

    # Extract the embedding data from the response
    data = response["data"]  # type: ignore

    # Return the embeddings as a list of lists of floats
    return [result["embedding"] for result in data]


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
def get_chat_completion(
    messages,
    model="gpt-3.5-turbo",  # use "gpt-4" for better results
    deployment_id=None,
):
    """
    Generate a chat completion using the configured provider.

    Supports OpenAI (default), Azure OpenAI, and MiniMax. When EMBEDDING_PROVIDER
    is set to "minimax", chat completions also use MiniMax's OpenAI-compatible API.

    Args:
        messages: The list of messages in the chat history.
        model: The name of the model to use for the completion. Default is gpt-3.5-turbo.

    Returns:
        A string containing the chat completion.

    Raises:
        Exception: If the API call fails.
    """
    response = {}

    if EMBEDDING_PROVIDER == "minimax":
        # MiniMax provides an OpenAI-compatible chat completion API
        if not MINIMAX_API_KEY:
            raise ValueError(
                "MINIMAX_API_KEY environment variable is required when using MiniMax."
            )
        response = openai.ChatCompletion.create(
            model=MINIMAX_CHAT_MODEL,
            messages=messages,
            api_key=MINIMAX_API_KEY,
            api_base=MINIMAX_API_BASE,
        )
    elif deployment_id is None:
        # Standard OpenAI
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
        )
    else:
        # Azure OpenAI
        response = openai.ChatCompletion.create(
            deployment_id=deployment_id,
            messages=messages,
        )

    choices = response["choices"]  # type: ignore
    completion = choices[0].message.content.strip()
    logger.info(f"Completion: {completion}")
    return completion
