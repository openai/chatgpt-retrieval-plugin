import pytest
import pulsar
from models.models import Document


class Producer:
    def send(self, *args, **kwargs):
        pass


class Message:
    def value(self):
        from mq.providers.pulsar_mq import DocumentSchema
        return DocumentSchema(id="test", text="test")


class Consumer:

    def acknowledge(self, msg):
        pass

    def negative_acknowledge(self, msg):
        pass

    def receive(self, *args, **kwargs):
        return Message()


@pytest.fixture
def get_producer():
    return Producer()


@pytest.fixture
def get_consumer():
    return Consumer()


@pytest.fixture
def mock_init_client(monkeypatch):
    monkeypatch.setattr(pulsar.Client, "__init__", lambda *args: None)


@pytest.fixture
def mock_create_producer(monkeypatch, get_producer):
    monkeypatch.setattr(pulsar.Client, "create_producer", lambda *args, **kwargs: get_producer)


@pytest.fixture
def mock_create_consumer(monkeypatch, get_consumer):
    monkeypatch.setattr(pulsar.Client, "subscribe", lambda *args, **kwargs: get_consumer)


@pytest.fixture
def mock_producer_send(monkeypatch):
    monkeypatch.setattr(pulsar.Producer, "send", lambda *args, **kwargs: None)


@pytest.fixture
def mock_callback():
    async def test(*args, **kwargs):
        pass

    return test


@pytest.fixture
def pulsar_mq(mock_init_client, mock_create_producer, mock_create_consumer):
    from mq.providers.pulsar_mq import PulsarMessageQueue
    return PulsarMessageQueue()


@pytest.mark.asyncio
async def test_produce(pulsar_mq):
    doc1 = Document(text="test")
    doc2 = Document(id="test", text="test")
    docs = [doc1, doc2]
    result = await pulsar_mq.produce(docs)
    assert result == docs


@pytest.mark.asyncio
async def test_consume(pulsar_mq, mock_callback):
    await pulsar_mq.consume_loop_helper(callback=mock_callback)
