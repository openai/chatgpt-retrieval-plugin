import os
import httpx
import httpx
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from loguru import logger
from dotenv import load_dotenv
from query_interface.chat_utils import call_chatgpt_api, get_queries
from dotenv import load_dotenv
from query_interface.chat_utils import call_chatgpt_api, get_queries

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryGPTRequest,
    QueryResponse,
    QueryGPTResponse,
    UpsertRequest,
    UpsertResponse,
    ZaloQueryRequest,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file

from models.models import DocumentMetadata, QueryGPT, Source
from models.models import DocumentMetadata, QueryGPT, Source

from query_interface.chat_utils import call_chatgpt_api

load_dotenv()

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

app.state.zalo_refresh_token = os.getenv("ZALO_REFRESH_TOKEN")

app.state.zalo_refresh_token = os.getenv("ZALO_REFRESH_TOKEN")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://mekong-gpt.fly.dev"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)


@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except:
        metadata_obj = DocumentMetadata(source=Source.file)

    document = await get_document_from_file(file, metadata_obj)

    try:
        ids = await datastore.upsert([document])
        return UpsertResponse(ids=ids)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
):
    try:
        ids = await datastore.upsert(request.documents)
        return UpsertResponse(ids=ids)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")
    
@app.post(
        "/zaloquery",
        # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
)
async def zaloquery(
        request: ZaloQueryRequest = Body(...),
):
    try:
        userid = request.sender.id
        userqn = request.message.text
        await querygpt_main(QueryGPTRequest(queries=[QueryGPT(query=userqn)], senderId=userid))
        return
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
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
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")
    
@app.post(
    "/querygpt",
    response_model=QueryGPTResponse,
)
async def querygpt_main(
    request: QueryGPTRequest = Body(...),
):
    try:
        userqn = request.queries.pop().query
        queries = get_queries(userqn)
        results = await datastore.query(
            queries
        )
        chunks = []
        for result in results:
            for inner_result in result.results:
                if inner_result.score < 0.35:
                    chunks.append(inner_result.text)
        response = call_chatgpt_api(userqn, chunks)

        if(request.senderId): # Send reply to Zalo user
            url = "https://openapi.zalo.me/v3.0/oa/message/cs" # Send POST request to Zalo API

            # Get the access token
            access_token = None
            async with httpx.AsyncClient() as client:
                r = await client.post("https://oauth.zaloapp.com/v4/oa/access_token", 
                                             headers = {
                                                 "Content-Type": "application/x-www-form-urlencoded",
                                                 "secret_key": os.getenv("ZALO_SECRET_KEY")},
                                             data = {
                                                 "refresh_token": app.state.zalo_refresh_token,
                                                 "app_id": "2857621919047997337",
                                                 "grant_type": "refresh_token"
                                             })
                response_json = r.json()
                if not "access_token" in response_json:
                    raise Exception("Cannot get the access token")

                app.state.zalo_refresh_token = response_json["refresh_token"]
                access_token = response_json["access_token"]

            headers = {
                "access_token": os.getenv("ZALO_ACCESS_TOKEN"),
                "Content-Type": "application/json",
            }

            data = {
                "recipient": {"user_id": request.senderId},
                "message": {"text": response["choices"][0]["message"]["content"]},
            }

            async with httpx.AsyncClient() as client:
                await client.post(url, headers=headers, json=data)

        return QueryGPTResponse(result=response["choices"][0]["message"]["content"])
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
