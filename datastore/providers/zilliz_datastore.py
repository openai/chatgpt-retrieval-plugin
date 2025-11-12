import os

from loguru import logger
from typing import Optional
from pymilvus import (
    connections,
)
from uuid import uuid4

from datastore.providers.milvus_datastore import (
    MilvusDataStore,
)


ZILLIZ_COLLECTION = os.environ.get("ZILLIZ_COLLECTION") or "c" + uuid4().hex
ZILLIZ_URI = os.environ.get("ZILLIZ_URI")
ZILLIZ_USER = os.environ.get("ZILLIZ_USER")
ZILLIZ_PASSWORD = os.environ.get("ZILLIZ_PASSWORD")
ZILLIZ_USE_SECURITY = False if ZILLIZ_PASSWORD is None else True

ZILLIZ_CONSISTENCY_LEVEL = os.environ.get("ZILLIZ_CONSISTENCY_LEVEL")


class ZillizDataStore(MilvusDataStore):
    def __init__(self, create_new: Optional[bool] = False):
        """Create a Zilliz DataStore.

        The Zilliz Datastore allows for storing your indexes and metadata within a Zilliz Cloud instance.

        Args:
            create_new (Optional[bool], optional): Whether to overwrite if collection already exists. Defaults to True.
        """
        # Overwrite the default consistency level by MILVUS_CONSISTENCY_LEVEL
        self._consistency_level = ZILLIZ_CONSISTENCY_LEVEL or "Bounded"
        self._create_connection()

        self._create_collection(ZILLIZ_COLLECTION, create_new)  # type: ignore
        self._create_index()

    def _create_connection(self):
        # Check if the connection already exists
        try:
            i = [
                connections.get_connection_addr(x[0])
                for x in connections.list_connections()
            ].index({"address": ZILLIZ_URI, "user": ZILLIZ_USER})
            self.alias = connections.list_connections()[i][0]
        except ValueError:
            # Connect to the Zilliz instance using the passed in Environment variables
            self.alias = uuid4().hex
            connections.connect(alias=self.alias, uri=ZILLIZ_URI, user=ZILLIZ_USER, password=ZILLIZ_PASSWORD, secure=ZILLIZ_USE_SECURITY)  # type: ignore
            logger.info("Connect to zilliz cloud server")

    def _create_index(self):
        try:
            # If no index on the collection, create one
            if len(self.col.indexes) == 0:
                self.index_params = {
                    "metric_type": "IP",
                    "index_type": "AUTOINDEX",
                    "params": {},
                }
                self.col.create_index("embedding", index_params=self.index_params)

            self.col.load()
            self.search_params = {"metric_type": "IP", "params": {}}
        except Exception as e:
            logger.error("Failed to create index, error: {}".format(e))
