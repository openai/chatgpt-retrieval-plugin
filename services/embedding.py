import os
from typing import List
from abc import ABC, abstractmethod

import services.openai

EMBEDDING_ENGINE = 'openai'
_instance = None


class Embedding(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    @staticmethod
    def instance() -> 'Embedding':
        global _instance

        if _instance is None:
            datastore = os.getenv("EMBEDDING_ENGINE", EMBEDDING_ENGINE)
            if datastore == 'openai':
                _instance = OpenaiEmbedding()
            elif datastore == 'sentence':
                _instance = SentenceTransformerEmbedding()
            else:
                raise ValueError(
                    f"Unsupported embedding engine: {datastore}. "
                    f"Try one of the following: openai, sentence"
                )

        return _instance


class OpenaiEmbedding(Embedding):
    @property
    def dimension(self) -> int:
        return 1536

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return services.openai.get_embeddings(texts)


class SentenceTransformerEmbedding(Embedding):
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    @property
    def dimension(self) -> int:
        return 384

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts).tolist()
