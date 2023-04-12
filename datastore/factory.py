import os
from datastore.providers import Providers
from datastore.datastore import DataStore


async def get_datastore() -> DataStore:
    datastore_options = [p.value for p in Providers]
    datastore = os.environ.get("DATASTORE")
    assert datastore is not None

    match datastore:
        case Providers.llama.value:
            from datastore.providers.llama_datastore import LlamaDataStore
            return LlamaDataStore()

        case Providers.pinecone.value:
            from datastore.providers.pinecone_datastore import PineconeDataStore

            return PineconeDataStore()
        case Providers.weaviate.value:
            from datastore.providers.weaviate_datastore import WeaviateDataStore

            return WeaviateDataStore()
        case Providers.milvus.value:
            from datastore.providers.milvus_datastore import MilvusDataStore

            return MilvusDataStore()
        case Providers.zilliz.value:
            from datastore.providers.zilliz_datastore import ZillizDataStore

            return ZillizDataStore()
        case Providers.redis.value:
            from datastore.providers.redis_datastore import RedisDataStore

            return await RedisDataStore.init()
        case Providers.qdrant.value:
            from datastore.providers.qdrant_datastore import QdrantDataStore

            return QdrantDataStore()
        case _:
            raise ValueError(
                f"Unsupported vector database: {datastore}. "
                f"Try one of the following: {datastore_options}"
            )
