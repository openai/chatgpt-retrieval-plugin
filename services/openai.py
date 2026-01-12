from typing import List
import openai
import os
from loguru import logger

from tenacity import retry, wait_random_exponential, stop_after_attempt

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", 256))

# DoS protection settings
OPENAI_TIMEOUT = int(os.environ.get("OPENAI_TIMEOUT", 30))  # seconds
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", 500))
MAX_INPUT_LENGTH = int(os.environ.get("MAX_INPUT_LENGTH", 10000))  # characters


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Embed texts using OpenAI's ada model.

    Args:
        texts: The list of texts to embed.

    Returns:
        A list of embeddings, each of which is a list of floats.

    Raises:
        Exception: If the OpenAI API call fails.
    """
    # Call the OpenAI API to get the embeddings
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
    max_tokens=None,
    timeout=None,
):
    """
    Generate a chat completion using OpenAI's chat completion API.

    Args:
        messages: The list of messages in the chat history.
        model: The name of the model to use for the completion. Default is gpt-3.5-turbo, which is a fast, cheap and versatile model. Use gpt-4 for higher quality but slower results.
        max_tokens: Maximum tokens in response (default: MAX_TOKENS env var or 500).
        timeout: Request timeout in seconds (default: OPENAI_TIMEOUT env var or 30).

    Returns:
        A string containing the chat completion.

    Raises:
        Exception: If the OpenAI API call fails.
        ValueError: If input exceeds maximum allowed length.
    """
    # Input validation to prevent DoS
    total_input_length = sum(len(m.get("content", "")) for m in messages)
    if total_input_length > MAX_INPUT_LENGTH:
        raise ValueError(f"Input length ({total_input_length}) exceeds maximum allowed ({MAX_INPUT_LENGTH})")

    # Use defaults if not specified
    max_tokens = max_tokens or MAX_TOKENS
    timeout = timeout or OPENAI_TIMEOUT

    # call the OpenAI chat completion API with the given messages
    # Note: Azure Open AI requires deployment id
    response = {}
    if deployment_id == None:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    else:
        response = openai.ChatCompletion.create(
            deployment_id=deployment_id,
            messages=messages,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    choices = response["choices"]  # type: ignore
    completion = choices[0].message.content.strip()
    logger.info(f"Completion: {completion}")
    return completion
