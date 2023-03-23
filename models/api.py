from models.models import (
    Document,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    Query,
    QueryResult,
)
from pydantic import BaseModel


class UpsertRequest(BaseModel):
    documents: list[Document]


class UpsertResponse(BaseModel):
    ids: list[str]


class QueryRequest(BaseModel):
    queries: list[Query]


class QueryResponse(BaseModel):
    results: list[QueryResult]


class DeleteRequest(BaseModel):
    ids: list[str] | None = None
    filter: DocumentMetadataFilter | None = None
    delete_all: bool | None = False


class DeleteResponse(BaseModel):
    success: bool
