from datastore.datastore import DataStore
import os


async def get_datastore() -> DataStore:
    datastore = os.environ.get("DATASTORE")
    assert datastore is not None

    match datastore:
        case "analyticdb":
            from datastore.providers.analyticdb_datastore import AnalyticDBDataStore

            return AnalyticDBDataStore()
        case "azuresearch":
            from datastore.providers.azuresearch_datastore import AzureSearchDataStore

            return AzureSearchDataStore()
        case "chroma":
            from datastore.providers.chroma_datastore import ChromaDataStore

            return ChromaDataStore()
        case "elasticsearch":
            from datastore.providers.elasticsearch_datastore import (
                ElasticsearchDataStore,
            )

            return ElasticsearchDataStore()
        case "llama":
            from datastore.providers.llama_datastore import LlamaDataStore

            return LlamaDataStore()
        case "milvus":
            from datastore.providers.milvus_datastore import MilvusDataStore

            return MilvusDataStore()
        case "pinecone":
            from datastore.providers.pinecone_datastore import PineconeDataStore

            return PineconeDataStore()
        case "postgres":
            from datastore.providers.postgres_datastore import PostgresDataStore

            return PostgresDataStore()
        case "qdrant":
            from datastore.providers.qdrant_datastore import QdrantDataStore

            return QdrantDataStore()
        case "redis":
            from datastore.providers.redis_datastore import RedisDataStore

            return await RedisDataStore.init()
        case "supabase":
            from datastore.providers.supabase_datastore import SupabaseDataStore

            return SupabaseDataStore()
        case "weaviate":
            from datastore.providers.weaviate_datastore import WeaviateDataStore

            return WeaviateDataStore()
        case "zilliz":
            from datastore.providers.zilliz_datastore import ZillizDataStore

            return ZillizDataStore()
        case _:
            raise ValueError(
                f"Unsupported vector database: {datastore}. "
                f"Try one of the following: analyticdb, azuresearch, chroma, elasticsearch, llama, milvus, pinecone, postgres, qdrant, redis, supabase, weaviate, or zilliz"
            )
