from enum import Enum


class Providers(Enum):
    redis = "redis"
    llama = "llama"
    milvus = "milvus"
    pinecone = "pinecone"
    weaviate = "weaviate"
    zilliz = "zilliz"
    qdrant ="qdrant"
