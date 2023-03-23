from pydantic import BaseModel
from enum import Enum


class Source(str, Enum):
    email = "email"
    file = "file"
    chat = "chat"


class DocumentMetadata(BaseModel):
    source: Source | None = None
    source_id: str | None = None
    url: str | None = None
    created_at: str | None = None
    author: str | None = None


class DocumentChunkMetadata(DocumentMetadata):
    document_id: str | None = None


class DocumentChunk(BaseModel):
    id: str | None = None
    text: str
    metadata: DocumentChunkMetadata
    embedding: list[float] | None = None


class DocumentChunkWithScore(DocumentChunk):
    score: float


class Document(BaseModel):
    id: str | None = None
    text: str
    metadata: DocumentMetadata | None = None


class DocumentWithChunks(Document):
    chunks: list[DocumentChunk]


class DocumentMetadataFilter(BaseModel):
    document_id: str | None = None
    source: Source | None = None
    source_id: str | None = None
    author: str | None = None
    start_date: str | None = None  # any date string format
    end_date: str | None = None  # any date string format


class Query(BaseModel):
    query: str
    filter: DocumentMetadataFilter | None = None
    top_k: int | None = 3


class QueryWithEmbedding(Query):
    embedding: list[float]


class QueryResult(BaseModel):
    query: str
    results: list[DocumentChunkWithScore]
