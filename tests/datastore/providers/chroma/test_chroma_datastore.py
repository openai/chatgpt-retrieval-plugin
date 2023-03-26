import pytest

from datastore.providers.chroma_datastore import ChromaDataStore
import chromadb

@pytest.fixture
def chroma_datastore() -> ChromaDataStore:
    client = chromadb.Client()
    ds = ChromaDataStore(client=client)

@pytest.mark.asyncio
async def test_noop(chroma_datastore):
    pass