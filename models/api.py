from models.models import (
    Document,
    DocumentMetadataFilter,
    Query,
    QueryGPT,
    QueryResult,
    QueryGPTResult,
    Sender,
    Message,
)
from pydantic import BaseModel
from typing import List, Optional


class UpsertRequest(BaseModel):
    documents: List[Document]


class UpsertResponse(BaseModel):
    ids: List[str]


class QueryRequest(BaseModel):
    queries: List[Query]

class ZaloQueryRequest(BaseModel):
    sender: Sender
    message: Message

class QueryGPTRequest(BaseModel):
    queries: List[QueryGPT]
    senderId: str

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
