# This is a version of the main.py file found in ../../../server/main.py for testing the plugin locally.
# Use the command `poetry run dev` to run this.
import os
from typing import List, Optional

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
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_get_request import AccountsGetRequest


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
    SyncItemRequest,
    SyncItemResponse,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file

from starlette.responses import FileResponse

from models.models import Document, DocumentMetadata, Source
from fastapi.middleware.cors import CORSMiddleware


plaid_client_id = os.environ.get("PLAID_CLIENT_ID")
plaid_secret = os.environ.get("PLAID_SECRET")

if plaid_client_id is None or plaid_secret is None:
    raise Exception("Plaid client id and secret must be set in environment variables")

plaid_configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': plaid_client_id,
        'secret': plaid_secret,
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
    body: InitializePlaidRequest = Body(...),
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


@app.post(
    "/sync-item",
    response_model=SyncItemResponse,
)
async def sync_item(
    body: SyncItemRequest = Body(...),
):
    # 1. Get transactions
    transactions_request = TransactionsSyncRequest(
        access_token=body.access_token,
    )

    transactions_response = plaid_client.transactions_sync(transactions_request)
    transactions = transactions_response['added']

    while (transactions_response['has_more']):
        transactions_request = TransactionsSyncRequest(
            access_token=body.access_token,
            cursor=transactions_response['next_cursor']
        )
        transactions_response = plaid_client.transactions_sync(transactions_request)
        transactions += transactions_response['added']
    dict_transactions = [t.to_dict() for t in transactions]

    # 2. Get accounts
    accounts_request = AccountsGetRequest(
        access_token=body.access_token,
    )
    accounts_response = plaid_client.accounts_get(accounts_request)
    accounts = accounts_response['accounts']
    dict_accounts = [a.to_dict() for a in accounts]

    # 3. Store transactions and accounts
    documents: List[Document] = []
    for t in transactions:
        documents.append(Document(text=str(t.to_dict()),
                                  metadata=DocumentMetadata(
                                        source=Source.plaid,
                                        source_id=t.transaction_id,
                                        # author=t.item_id,
                                  )))
    for a in accounts:
        documents.append(Document(text=str(a.to_dict()),
                                  metadata=DocumentMetadata(
                                        source=Source.plaid,
                                        source_id=a.account_id,
                                        # author=a.item_id,
                                  )))

    ids = await datastore.upsert(documents)

    return SyncItemResponse(success=True, transactions=dict_transactions, accounts=dict_accounts)

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("local-server.main:app", host="localhost", port=PORT, reload=True)
