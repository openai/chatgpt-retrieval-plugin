import os
from typing import Dict, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from auth.auth_bearer import GetCurrentUser
from datastore.factory import get_datastore
from models.api import (DeleteRequest, DeleteResponse, QueryRequest,
                        QueryResponse, UpsertRequest, UpsertResponse, User)
from services.file import get_document_from_file

load_dotenv()

app = FastAPI(dependencies=[Depends(GetCurrentUser())])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(GetCurrentUser())],
)
app.mount("/sub", sub_app)


@app.post(
    "/upsert-file/{index_name}",
    response_model=UpsertResponse,
)
async def upsert_file(
    index_name: str,
    file: UploadFile = File(...),
    document_id: Optional[str] = None,
    user: Dict = Depends(GetCurrentUser()),
):
    document = await get_document_from_file(file, document_id)

    try:
        ids = await datastore.upsert([document], organization_id = user.organization_id, index_name=index_name)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
    user: Dict = Depends(GetCurrentUser()),
):
    try:
        ids = await datastore.upsert(request.documents, organization_id=user.organization_id, index_name=request.index_name)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",   
    response_model=QueryResponse,
)
async def query_main(
    request: QueryRequest = Body(...),
    user: User = Depends(GetCurrentUser()),
):
    try:
        results = await datastore.query(
            request.queries,
            organization_id=user.organization_id,
            index_name=request.index_name,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
    user: Dict = Depends(GetCurrentUser()),
):
    try:
        results = await datastore.query(
            request.queries,
            organization_id=user.organization_id,
            index_name=request.index_name,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
    user: Dict = Depends(GetCurrentUser()),
):
    if not (request.ids or request.filter or request.delete_all or request.index_name):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, index_name, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
            organization_id=user.organization_id,
            index_name=request.index_name,
        )
        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    portStr = os.environ.get('PORT')
    port = int(portStr) if portStr else 8000
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, reload=True)
