import json

from django.core.management.base import BaseCommand

from app.event_bus import build_consumer
from app.models import Order


# ADDED-ASSIGNMENT06: saga orchestrator listens for reservation events and applies compensation.
class Command(BaseCommand):
    help = "Run order saga worker"

    def handle(self, *args, **options):
        connection, channel = build_consumer(
            queue_name="order.saga.events",
            binding_keys=["payment.reserved", "payment.failed", "shipping.reserved", "shipping.failed"],
        )

        def _process(_ch, method, _props, body):
            payload = json.loads(body.decode("utf-8"))
            order_id = payload.get("order_id")
            reason = payload.get("reason", "")

            try:
                order = Order.objects.get(pk=order_id)
            except Order.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Order {order_id} not found"))
                return

            if method.routing_key == "payment.reserved":
                order.payment_reserved = True
            elif method.routing_key == "shipping.reserved":
                order.shipping_reserved = True
            else:
                order.status = "CANCELED"
                order.compensation_reason = reason or method.routing_key

            if order.status != "CANCELED" and order.payment_reserved and order.shipping_reserved:
                order.status = "CONFIRMED"

            order.save()
            self.stdout.write(self.style.SUCCESS(f"Saga update order={order.id} status={order.status}"))

        channel.basic_consume(
            queue="order.saga.events",
            on_message_callback=lambda ch, method, props, body: (_process(ch, method, props, body), ch.basic_ack(method.delivery_tag)),
        )
        self.stdout.write(self.style.SUCCESS("Order saga worker started"))
        try:
            channel.start_consuming()
        finally:
            connection.close()
