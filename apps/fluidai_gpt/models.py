from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class Source(str, Enum):
    email = "email"
    file = "file"
    chat = "chat"


class DocumentMetadata(BaseModel):
    source: Optional[Source] = None
    source_id: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None


class PassageMetadata(BaseModel):
    source: Optional[Source] = None
    source_id: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None


class QueryResult(BaseModel):
    query: str
    result: str

class CloudUploadMetadata(BaseModel):
    destination_path: str
    upload_file_path: Optional[str] = None
    data_to_upload: Optional[str] = None
    upload_file_name: Optional[str] = None

class CloudDownloadMetadata(BaseModel):
    destination_path: str
    file_path: str

class CloudDataMetadata(BaseModel):
    cloud_file_path: str
    file_buffer: str



