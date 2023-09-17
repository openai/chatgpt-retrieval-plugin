from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryGPT,
    QueryResult,
    QueryGPTResult,
)
from pydantic import BaseModel
from typing import List, Optional


class UpsertRequest(BaseModel):
    documents: List[Document]


class UpsertResponse(BaseModel):
    ids: List[str]


class QueryRequest(BaseModel):
    queries: List[Query]

class QueryGPTRequest(BaseModel):
    queries: List[QueryGPT]

class QueryResponse(BaseModel):
    results: List[QueryResult]

class QueryGPTResponse(BaseModel):
    result: str

class DeleteRequest(BaseModel):
    ids: Optional[List[str]] = None
    filter: Optional[DocumentMetadataFilter] = None
    delete_all: Optional[bool] = False


class DeleteResponse(BaseModel):
    success: bool
