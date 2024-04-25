from datastore.datastore import DataStore
import os


async def get_datastore() -> DataStore:
    datastore = os.environ.get("DATASTORE")
    assert datastore is not None

    match datastore:
        case "chroma":
            from datastore.providers.chroma_datastore import ChromaDataStore

            return ChromaDataStore()
        case "llama":
            from datastore.providers.llama_datastore import LlamaDataStore

            return LlamaDataStore()

        case "pinecone":
            from datastore.providers.pinecone_datastore import PineconeDataStore

            return PineconeDataStore()
        case "weaviate":
            from datastore.providers.weaviate_datastore import WeaviateDataStore

            return WeaviateDataStore()
        case "milvus":
            from datastore.providers.milvus_datastore import MilvusDataStore

            return MilvusDataStore()
        case "zilliz":
            from datastore.providers.zilliz_datastore import ZillizDataStore

            return ZillizDataStore()
        case "redis":
            from datastore.providers.redis_datastore import RedisDataStore

            return await RedisDataStore.init()
        case "azurecosmosdb":
            from datastore.providers.azurecosmosdb_datastore import (
                AzureCosmosDBDataStore,
            )

            return await AzureCosmosDBDataStore.create()
        case "qdrant":
            from datastore.providers.qdrant_datastore import QdrantDataStore

            return QdrantDataStore()
        case "azuresearch":
            from datastore.providers.azuresearch_datastore import AzureSearchDataStore

            return AzureSearchDataStore()
        case "supabase":
            from datastore.providers.supabase_datastore import SupabaseDataStore

            return SupabaseDataStore()
        case "postgres":
            from datastore.providers.postgres_datastore import PostgresDataStore

            return PostgresDataStore()
        case "analyticdb":
            from datastore.providers.analyticdb_datastore import AnalyticDBDataStore

            return AnalyticDBDataStore()
        case "elasticsearch":
            from datastore.providers.elasticsearch_datastore import (
                ElasticsearchDataStore,
            )

            return ElasticsearchDataStore()
        case "mongodb-atlas":
            from datastore.providers.mongodb_atlas_datastore import (
                MongoDBAtlasDataStore,
            )

            return MongoDBAtlasDataStore()
        case _:
            raise ValueError(
                f"Unsupported vector database: {datastore}. "
                f"Try one of the following: mongodb-atlas, llama, elasticsearch, pinecone, weaviate, milvus, zilliz, redis, azuresearch, or qdrant"
            )
