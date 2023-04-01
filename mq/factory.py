import os

from mq.mq import MessageQueue


async def get_message_queue() -> MessageQueue:
    message_queue = os.environ.get("MQ")
    if message_queue:
        match message_queue:
            case 'pulsar':
                from mq.providers.pulsar_mq import PulsarMessageQueue
                return PulsarMessageQueue()
            case _:
                raise ValueError(f"Unsupported message queue: {message_queue}")
