from typing import List
import os
from loguru import logger

from tenacity import retry, wait_random_exponential, stop_after_attempt
from openai import AzureOpenAI, OpenAI

# Azure Open AI is configured with a dedicated client; the 0.x SDK read
# OPENAI_API_TYPE / OPENAI_API_BASE into module-level globals instead.
if os.environ.get("OPENAI_API_TYPE") == "azure":
    client = AzureOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        azure_endpoint=os.environ["OPENAI_API_BASE"],
        api_version=os.environ.get("OPENAI_API_VERSION", "2023-05-15"),
    )
else:
    client = OpenAI()

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", 256))


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
        response = client.embeddings.create(input=texts, model=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMENSION)
    else:
        response = client.embeddings.create(input=texts, model=deployment)

    # Extract the embedding data from the response
    data = response.data  # type: ignore

    # Return the embeddings as a list of lists of floats
    return [result.embedding for result in data]


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
def get_chat_completion(
    messages,
    model="gpt-3.5-turbo",  # use "gpt-4" for better results
    deployment_id=None,
):
    """
    Generate a chat completion using OpenAI's chat completion API.

    Args:
        messages: The list of messages in the chat history.
        model: The name of the model to use for the completion. Default is gpt-3.5-turbo, which is a fast, cheap and versatile model. Use gpt-4 for higher quality but slower results.

    Returns:
        A string containing the chat completion.

    Raises:
        Exception: If the OpenAI API call fails.
    """
    # call the OpenAI chat completion API with the given messages
    # Note: Azure Open AI requires deployment id
    response = {}
    if deployment_id == None:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    else:
        response = client.chat.completions.create(
            model=deployment_id,
            messages=messages,
        )

    choices = response.choices  # type: ignore
    completion = choices[0].message.content.strip()
    logger.info(f"Completion: {completion}")
    return completion
