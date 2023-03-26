# This is a version of the main.py file found in ../../../server/main.py with message queue.
# Copy and paste this into the main file at ../../../server/main.py if you choose to use message queue for your retrieval plugin.
import hashlib
import os
import uvicorn
from fastapi import FastAPI, File, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from loguru import logger

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from datastore.factory import get_datastore
from mq.factory import get_message_queue
from services.file import get_document_from_file

app = FastAPI()
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Create a sub-application, in order to access just the query endpoints in the OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
)
app.mount("/sub", sub_app)

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


@sub_app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
        file: UploadFile = File(...),
        token: HTTPAuthorizationCredentials = Depends(validate_token),
):
    document = await get_document_from_file(file)

    try:
        ids = await datastore.upsert([document])
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@sub_app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
        request: UpsertRequest = Body(...),
        token: HTTPAuthorizationCredentials = Depends(validate_token),
):
    try:
        documents = await message_queue.produce(request.documents)
        ids = [doc.id if doc.id else hashlib.sha256(doc.text.encode('utf-8')).hexdigest() for doc in documents]
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
        request: QueryRequest = Body(...),
        token: HTTPAuthorizationCredentials = Depends(validate_token),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    description="Accepts search query objects with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
        request: QueryRequest = Body(...),
        token: HTTPAuthorizationCredentials = Depends(validate_token),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
        request: DeleteRequest = Body(...),
        token: HTTPAuthorizationCredentials = Depends(validate_token),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.on_event("startup")
async def startup():
    global datastore, message_queue
    datastore = await get_datastore()
    message_queue = await get_message_queue()
    if message_queue:
        await message_queue.consume(datastore.upsert)


@app.on_event("shutdown")
async def shutdown():
    if message_queue:
        await message_queue.close()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
