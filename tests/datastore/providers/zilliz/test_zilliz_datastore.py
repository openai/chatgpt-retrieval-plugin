# from pathlib import Path
# from dotenv import find_dotenv, load_dotenv
# env_path = Path(".") / "zilliz.env"
# load_dotenv(dotenv_path=env_path, verbose=True)

import pytest

from datastore.providers.zilliz_datastore import (
    ZillizDataStore,
)

from datastore.providers.milvus_datastore import (
    EMBEDDING_FIELD,
)

# Note: Only do basic test here, the ZillizDataStore is derived from MilvusDataStore.

@pytest.fixture
def zilliz_datastore():
    return ZillizDataStore()


@pytest.mark.asyncio
async def test_zilliz(zilliz_datastore):
    assert True == zilliz_datastore.col.has_index()
    index_list = [x.to_dict() for x in zilliz_datastore.col.indexes]
    for index in index_list:
        if index['index_name'] == EMBEDDING_FIELD:
            assert 'AUTOINDEX' == index['index_param']['index_type']