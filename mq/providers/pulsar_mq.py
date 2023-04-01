import asyncio
import os
import threading

import pulsar
from loguru import logger
from pulsar import ConsumerType
from pulsar.schema import Record, String, AvroSchema

from enum import Enum
from typing import List, Callable

from models.models import Document
from mq.mq import MessageQueue

PULSAR_WEBSERVICE_URL = os.environ.get("PULSAR_WEBSERVICE_URL", "http://localhost:8080")
PULSAR_BROKER_SERVICE_URL = os.environ.get("PULSAR_BROKER_SERVICE_URL", "pulsar://localhost:6650")
PULSAR_AUTH_PLUGIN = os.environ.get("PULSAR_AUTH_PLUGIN")
PULSAR_AUTH_PARAMS = os.environ.get("PULSAR_AUTH_PARAMS")
PULSAR_TOPIC_NAME = os.environ.get("PULSAR_TOPIC_NAME", "chatgpt-retrival-plugin")


class Source(str, Enum):
    email = "email"
    file = "file"
    chat = "chat"


class DocumentMetadata(Record):
    source = Source
    source_id = String()
    url = String()
    created_at = String()
    author = String()


class DocumentSchema(Record):
    id = String()
    text = String()
    metadata = DocumentMetadata()


if PULSAR_AUTH_PLUGIN:
    match PULSAR_AUTH_PLUGIN:
        case "org.apache.pulsar.client.impl.auth.oauth2.AuthenticationOAuth2":
            client = pulsar.Client(PULSAR_BROKER_SERVICE_URL,
                                   authentication=pulsar.AuthenticationOauth2(PULSAR_AUTH_PARAMS))
        case _:
            client = pulsar.Client(PULSAR_BROKER_SERVICE_URL)
else:
    client = pulsar.Client(PULSAR_BROKER_SERVICE_URL)
producer = client.create_producer(PULSAR_TOPIC_NAME, schema=AvroSchema(DocumentSchema))
consumer = client.subscribe(PULSAR_TOPIC_NAME, f'{PULSAR_TOPIC_NAME}-subscription',
                            consumer_type=ConsumerType.Shared,
                            schema=AvroSchema(DocumentSchema))


class PulsarMessageQueue(MessageQueue):
    async def produce(self, documents: List[Document]) -> List[Document]:
        success_produce_docs = []
        for _doc in documents:
            try:
                _metadata = _doc.metadata
                if _metadata:
                    metadata = DocumentMetadata(source=Source(_metadata.source), source_id=_metadata.source_id,
                                                url=_metadata.url,
                                                created_at=_metadata.created_at, author=_metadata.author)
                    doc = DocumentSchema(id=_doc.id, text=_doc.text, metadata=metadata)
                else:
                    doc = DocumentSchema(id=_doc.id, text=_doc.text, metadata=DocumentMetadata())
                producer.send(doc)
                success_produce_docs.append(_doc)
            except Exception as e:
                logger.error(f"Produce doc {_doc.text} error {e}")
        return success_produce_docs

    async def consume_loop_helper(self, callback: Callable, *args, **kwargs):
        msg = consumer.receive()
        try:
            _doc = msg.value()
            doc = Document(id=_doc.id, text=_doc.text, metadata=_doc.metadata.__dict__)
            await callback([doc], *args, **kwargs)
            consumer.acknowledge(msg)
        except Exception as e:
            logger.error(f"Consume msg error {e}")
            consumer.negative_acknowledge(msg)

    async def consume_loop(self, callback: Callable, *args, **kwargs):
        while True:
            await self.consume_loop_helper(callback, *args, **kwargs)

    async def consume(self, callback: Callable, *args, **kwargs):
        threading.Thread(target=asyncio.run, args=(self.consume_loop(callback, *args, **kwargs),),
                         name="pulsar-consumer").start()

    async def close(self):
        client.close()
