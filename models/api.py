from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryResult,
)
from pydantic import BaseModel
from typing import List, Optional


class UpsertRequest(BaseModel):
    documents: List[Document]


class UpsertResponse(BaseModel):
    ids: List[str]


class QueryRequest(BaseModel):
    queries: List[Query]


class QueryResponse(BaseModel):
    results: List[QueryResult]


class DeleteRequest(BaseModel):
    ids: Optional[List[str]] = None
    filter: Optional[DocumentMetadataFilter] = None
    delete_all: Optional[bool] = False


class DeleteResponse(BaseModel):
    success: bool


class InitializePlaidRequest(BaseModel):
    client: str


class InitializePlaidResponse(BaseModel):
    success: bool
    link_token: str


class ExchangePublicTokenRequest(BaseModel):
    public_token: str


class ExchangePublicTokenResponse(BaseModel):
    success: bool
    access_token: str
