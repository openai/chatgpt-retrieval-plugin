from typing import List
from google.cloud import storage
from io import BufferedReader, BytesIO
from models.models import Document, DocumentMetadata, Source
from services.chunks import get_text_chunks
from services.file import extract_text_from_file

import mimetypes

async def get_index_documents_from_gcs_file(bucket_name: str, file_name: str) -> List[Document]:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    # get content reader
    contents = blob.download_as_bytes()
    bytes_io = BytesIO(contents)
    reader = BufferedReader(bytes_io)

    # get content mimetype
    mimetype = blob.content_type
    if mimetype is None:
        mimetype, _ = mimetypes.guess_type(file_name)
    if not mimetype:
        if file_name.endswith(".md"):
            # this needs special handling
            mimetype = "text/markdown"
        else:
            raise Exception("Unsupported file type")

    text = extract_text_from_file(reader, mimetype)
    text_chunks = get_text_chunks(text)

    metadata = DocumentMetadata(
        source=Source.file,
        url=f"https://storage.cloud.google.com/{bucket_name}/{file_name}",
    )

    documents = []
    for chunk in text_chunks:
        documents.append(
            Document(
                text=chunk,
                metadata=metadata
            )
        )

    return documents
