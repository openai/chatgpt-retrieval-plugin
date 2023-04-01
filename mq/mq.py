from abc import ABC, abstractmethod
from typing import List, Callable

from models.models import Document


class MessageQueue(ABC):
    @abstractmethod
    async def produce(self, documents: List[Document]) -> List[Document]:
        """
        Takes in a list of documents and sends to message queue
        """
        raise NotImplementedError

    @abstractmethod
    async def consume(self, callback: Callable, *args, **kwargs):
        """
        Invoke callback to consume the produced documents
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        """
        Clean MQ resources
        """
        raise NotImplementedError
