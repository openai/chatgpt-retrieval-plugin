from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class Source(str, Enum):
    email = "email"
    file = "file"
    chat = "chat"


class DocumentMetadata(BaseModel):
    name: Optional[str] = None
    parents: Optional[str] = None
    mimeType: Optional[str] = None
    originalFileSource: Optional[str] = None
    originalOwnersName: Optional[str] = None
    originalModifiedTime: Optional[str] = None
    originalOwnersEmail: Optional[str] = None
    originalCreatedTime: Optional[str] = None


class DocumentChunkMetadata(DocumentMetadata):
    document_id: Optional[str] = None


class DocumentChunk(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: DocumentChunkMetadata
    embedding: Optional[List[float]] = None


class DocumentChunkWithScore(DocumentChunk):
    score: float


class Document(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: Optional[DocumentMetadata] = None


class DocumentWithChunks(Document):
    chunks: List[DocumentChunk]


class DocumentMetadataFilter(BaseModel):
    name: Optional[str] = None
    parents: Optional[str] = None
    mimeType: Optional[str] = None
    originalFileSource: Optional[str] = None
    originalOwnersName: Optional[str] = None
    originalModifiedTime: Optional[str] = None
    originalOwnersEmail: Optional[str] = None
    originalCreatedTime: Optional[str] = None
    createdTimeStartDate: Optional[str] = None  # any date string format
    createdTimeEndDate: Optional[str] = None  # any date string format
    modifiedTimeStartDate: Optional[str] = None  # any date string format
    modifiedTimeEndDate: Optional[str] = None  # any date string format

class Query(BaseModel):
    query: str
    filter: Optional[DocumentMetadataFilter] = None
    top_k: Optional[int] = 3


class QueryWithEmbedding(Query):
    embedding: List[float]


class QueryResult(BaseModel):
    query: str
    results: List[DocumentChunkWithScore]
