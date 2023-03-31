from typing import List, Optional

from pydantic import BaseModel

from models.models import Document, DocumentMetadataFilter, Query, QueryResult


class UpsertRequest(BaseModel):
    documents: List[Document]
    index_name: Optional[str] = None


class UpsertResponse(BaseModel):
    ids: List[str]


class QueryRequest(BaseModel):
    queries: List[Query]
    index_name: Optional[str] = None


class QueryResponse(BaseModel):
    results: List[QueryResult]


class DeleteRequest(BaseModel):
    index_name: Optional[str] = None
    ids: Optional[List[str]] = None
    filter: Optional[DocumentMetadataFilter] = None
    delete_all: Optional[bool] = False


class DeleteResponse(BaseModel):
    success: bool

class User(BaseModel):
    account_id: str | None
    organization_id: str
    app_role: str | None
    token: str