from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import asyncio

from models.models import (
    Document,
    DocumentChunk,
    DocumentMetadataFilter,
    Query,
    QueryResult,
    QueryWithEmbedding,
)
from services.chunks import get_document_chunks
from services.openai import get_embeddings


def update_data_store(data_store):
    global data_store_object
    data_store_object = data_store


async def query(queries: List[Query]) -> List[QueryResult]:
    """
    Takes in a list of queries and filters and returns a list of query results with matching document chunks and scores.
    """
    # get a list of of just the queries from the Query list
    query_texts = [query.query for query in queries]
    query_embeddings = get_embeddings(query_texts)
    # hydrate the queries with embeddings
    queries_with_embeddings = [
        QueryWithEmbedding(**query.dict(), embedding=embedding)
        for query, embedding in zip(queries, query_embeddings)
    ]
    return await data_store_object._query(queries_with_embeddings)


async def upsert(
        documents: List[Document], chunk_token_size: Optional[int] = None
) -> List[str]:
    """
    Takes in a list of documents and inserts them into the database.
    Checks if the document exists in the index, inserts only if it doesnt exist.
    Return a list of document ids.
    """
    # Delete any existing vectors for documents with the input document ids

    chunks = get_document_chunks(documents, chunk_token_size)

    return await data_store_object._upsert(chunks)
