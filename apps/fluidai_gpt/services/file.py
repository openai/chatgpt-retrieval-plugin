from services.file import extract_text_from_filepath
import hashlib
from fastapi import UploadFile
import os
import time

from models.models import Document
from apps.fluidai_gpt.models import DocumentMetadata


async def get_document_from_file(file: UploadFile) -> Document:
    extracted_text, document_hash, file_stream = await extract_text_from_form_file(file)
    print(f"extracted_text:")
    # get metadata
    metadata = DocumentMetadata()
    doc = Document(text=extracted_text, metadata=metadata, id=document_hash)

    return doc


def generate_hash(document):
    """Generates the hash of the document"""
    # check if the document is a string and then encode it
    if type(document) == str:
        document = document.encode('utf-8')

    # generate hash only if document is in bytes format
    if type(document) == bytes:
        return hashlib.sha256(document).hexdigest()
    else:
        print('Document cannot be hashed')
        return False


async def extract_text_from_form_file(file: UploadFile):
    """Return the file stream of a file."""
    # get the file body from the upload file object
    mimetype = file.content_type
    print(f"mimetype: {mimetype}")
    print(f"file.file: {file.file}")
    print("file: ", file)

    file_stream = await file.read()

    # generate the hash using the file stream
    document_hash = generate_hash(file_stream)

    # save the document locally
    temp_file_path = f"/tmp/{document_hash}"

    # write the file to a temporary location
    with open(temp_file_path, "wb") as f:
        f.write(file_stream)

    try:
        extracted_text = extract_text_from_filepath(temp_file_path, mimetype)
    except Exception as e:
        print(f"Error: {e}")
        os.remove(temp_file_path)
        raise e

    # remove file from temp location
    os.remove(temp_file_path)

    return extracted_text, document_hash, file_stream
