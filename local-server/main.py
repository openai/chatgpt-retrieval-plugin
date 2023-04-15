# This is a version of the main.py file found in ../../../server/main.py for testing the plugin locally.
# Use the command `poetry run dev` to run this.
import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Body, UploadFile

import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.link_token_account_filters import LinkTokenAccountFilters
from plaid.model.depository_filter import DepositoryFilter
from plaid.model.depository_account_subtypes import DepositoryAccountSubtypes
from plaid.model.depository_account_subtype import DepositoryAccountSubtype
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest


from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
    InitializePlaidRequest,
    InitializePlaidResponse,
    ExchangePublicTokenRequest,
    ExchangePublicTokenResponse,
    TransactionResponse,
    AccountResponse
)
from datastore.factory import get_datastore
from services.file import get_document_from_file

from starlette.responses import FileResponse

from models.models import DocumentMetadata, Source
from fastapi.middleware.cors import CORSMiddleware


plaid_configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': os.environ.get("PLAID_CLIENT_ID"),
        'secret': os.environ.get("PLAID_SECRET"),
    }
)

plaid_api_client = plaid.ApiClient(plaid_configuration)
plaid_client = plaid_api.PlaidApi(plaid_api_client)

app = FastAPI()

PORT = 3333

origins = [
    f"http://localhost:{PORT}",
    "https://chat.openai.com",
    "http://localhost:3000",  # for ui
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.route("/.well-known/ai-plugin.json")
async def get_manifest(request):
    file_path = "./local-server/ai-plugin.json"
    return FileResponse(file_path, media_type="text/json")


@app.route("/.well-known/logo.png")
async def get_logo(request):
    file_path = "./local-server/logo.png"
    return FileResponse(file_path, media_type="text/json")


@app.route("/.well-known/openapi.yaml")
async def get_openapi(request):
    file_path = "./local-server/openapi.yaml"
    return FileResponse(file_path, media_type="text/json")


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
        print("Error:", e)
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
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post("/query", response_model=QueryResponse)
async def query_main(request: QueryRequest = Body(...)):
    try:
        results = await datastore.query(
            request.queries,
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


@app.post(
    "/create-link-token",
    response_model=InitializePlaidResponse,
)
async def create_link_token(
    request: InitializePlaidRequest = Body(...),
):
    request = LinkTokenCreateRequest(
        products=[Products('auth'), Products('transactions')],
        client_name="Plaid Test App",
        country_codes=[CountryCode('US')],
        # redirect_uri='',
        language='en',
        webhook='https://example.com',
        link_customization_name='default',
        account_filters=LinkTokenAccountFilters(
            depository=DepositoryFilter(
                account_subtypes=DepositoryAccountSubtypes(
                    [DepositoryAccountSubtype('checking'), DepositoryAccountSubtype('savings')]
                )
            )
        ),
        user=LinkTokenCreateRequestUser(
            client_user_id='123-test-user-id'
        ),
    )
    response = plaid_client.link_token_create(request)
    link_token = response['link_token']
    print(f"link_token: {link_token}")
    return InitializePlaidResponse(success=True, link_token=link_token)


@app.post(
    "/exchange-public-token",
    response_model=ExchangePublicTokenResponse,
)
async def exchange_public_token(
    request: ExchangePublicTokenRequest = Body(...),
):
    exchange_token_request = ItemPublicTokenExchangeRequest(
        public_token=request.public_token,
    )
    response = plaid_client.item_public_token_exchange(exchange_token_request)
    return ExchangePublicTokenResponse(success=True, access_token=response['access_token'])


@app.get(
    "/transactions",
    response_model=TransactionResponse,
)
async def get_transactions():
    """
    Get most recent 20 transactions.
    TODO: Shove to LLAMAIndex for Text to SQL
    # https://gpt-index.readthedocs.io/en/latest/guides/tutorials/sql_guide.html#text-to-sql-basic
    """
    # response = datastore.query(
    #     "What are the 20 most recent transactions?"
    # )
    # return response, response.extra_info['sql_query']
    return datastore.query(
        "SELECT * FROM transactions ORDER BY date DESC LIMIT 20"
    )


@app.get(
    "/all_transactions",
    response_model=TransactionResponse,
)
async def get_all_transactions():
    """
    Get all of the transactions.
    TODO: Shove to LLAMAIndex for Text to SQL
    # https://gpt-index.readthedocs.io/en/latest/guides/tutorials/sql_guide.html#text-to-sql-basic
    """
    # response = datastore.query(
    #     "What are all of the transactions?"
    # )
    # return response, response.extra_info['sql_query']
    return datastore.query(
        "SELECT * FROM transactions"
    )


@app.get(
    "/account",
    response_model=AccountResponse,
)
async def get_account():
    """
    Get all of the transactions.
    TODO: Shove to LLAMAIndex for Text to SQL
    # https://gpt-index.readthedocs.io/en/latest/guides/tutorials/sql_guide.html#text-to-sql-basic
    """
    # response = datastore.query(
    #     "What are all of my account information?"
    # )
    # return response, response.extra_info['sql_query']
    return datastore.query(
        "SELECT * FROM accounts"
    )

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("local-server.main:app", host="localhost", port=PORT, reload=True)
