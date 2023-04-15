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
    document_id: Optional[str] = None
    source: Optional[Source] = None
    source_id: Optional[str] = None
    author: Optional[str] = None
    start_date: Optional[str] = None  # any date string format
    end_date: Optional[str] = None  # any date string format


class Query(BaseModel):
    query: str
    filter: Optional[DocumentMetadataFilter] = None
    top_k: Optional[int] = 3


class QueryWithEmbedding(Query):
    embedding: List[float]


class QueryResult(BaseModel):
    query: str
    results: List[DocumentChunkWithScore]

class Transaction(BaseModel):
    """Dataclass for Plaid transactions.
    [
        {
        "account_id": "BxBXxLj1m4HMXBm9WZZmCWVbPjX16EHwv99vp",
        "amount": 2307.21,
        "iso_currency_code": "USD",
        "unofficial_currency_code": null,
        "category": [
            "Shops",
            "Computers and Electronics"
        ],
        "category_id": "19013000",
        "check_number": null,
        "date": "2017-01-29",
        "datetime": "2017-01-27T11:00:00Z",
        "authorized_date": "2017-01-27",
        "authorized_datetime": "2017-01-27T10:34:50Z",
        "location": {
            "address": "300 Post St",
            "city": "San Francisco",
            "region": "CA",
            "postal_code": "94108",
            "country": "US",
            "lat": 40.740352,
            "lon": -74.001761,
            "store_number": "1235"
        },
        "name": "Apple Store",
        "merchant_name": "Apple",
        "payment_meta": {
            "by_order_of": null,
            "payee": null,
            "payer": null,
            "payment_method": null,
            "payment_processor": null,
            "ppd_id": null,
            "reason": null,
            "reference_number": null
        },
        "payment_channel": "in store",
        "pending": false,
        "pending_transaction_id": null,
        "account_owner": null,
        "transaction_id": "lPNjeW1nR6CDn5okmGQ6hEpMo4lLNoSrzqDje",
        "transaction_code": null,
        "transaction_type": "place"
        }
    ],
    """
    account_id: str
    amount: float
    iso_currency_code: str
    unofficial_currency_code: Optional[str] = None
    category: List[str]
    category_id: str
    check_number: Optional[str] = None
    date: str
    datetime: str
    authorized_date: str
    authorized_datetime: str
    location: Optional[dict] = None
    name: str
    merchant_name: str
    payment_meta: Optional[dict] = None
    payment_channel: str
    pending: bool
    pending_transaction_id: Optional[str] = None
    account_owner: Optional[str] = None
    transaction_id: str
    transaction_code: Optional[str] = None
    transaction_type: str
    

class Account(BaseModel):
    """Dataclass for Plaid accounts.
    https://plaid.com/docs/api/products/transactions/#transactionsget
     {
      "account_id": "BxBXxLj1m4HMXBm9WZZmCWVbPjX16EHwv99vp",
      "balances": {
        "available": 110,
        "current": 110,
        "iso_currency_code": "USD",
        "limit": null,
        "unofficial_currency_code": null
      },
      "mask": "0000",
      "name": "Plaid Checking",
      "official_name": "Plaid Gold Standard 0% Interest Checking",
      "subtype": "checking",
      "type": "depository"
    }
    """
    id: str
    available_balance: float
    current_balance: float
    iso_currency_code: str
    unofficial_currency_code: Optional[str] = None
    limit: Optional[float] = None
    mask: str
    name: str
    official_name: str
    subtype: str
    type: str
