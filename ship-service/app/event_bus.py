import json
import os
import time

import pika


# ADDED-ASSIGNMENT06: RabbitMQ utilities for shipping reservation worker.
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
EVENT_EXCHANGE = "bookstore.events"


def _connect_with_retry(max_attempts=30, delay=2):
    last_exc = None
    for _ in range(max_attempts):
        try:
            return pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        except pika.exceptions.AMQPError as exc:
            last_exc = exc
            time.sleep(delay)
    raise RuntimeError(f"Cannot connect RabbitMQ: {last_exc}")


def publish_event(routing_key, payload):
    connection = _connect_with_retry()
    try:
        channel = connection.channel()
        channel.exchange_declare(exchange=EVENT_EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=EVENT_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        connection.close()


def build_consumer(queue_name, binding_keys):
    connection = _connect_with_retry()
    channel = connection.channel()
    channel.exchange_declare(exchange=EVENT_EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=queue_name, durable=True)
    for key in binding_keys:
        channel.queue_bind(exchange=EVENT_EXCHANGE, queue=queue_name, routing_key=key)
    channel.basic_qos(prefetch_count=1)
    return connection, channel
