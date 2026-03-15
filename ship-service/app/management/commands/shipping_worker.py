import json
import time

from django.core.management.base import BaseCommand

from app.event_bus import build_consumer, publish_event
from app.models import Shipment


# ADDED-ASSIGNMENT06: shipping participant in Saga reserve step.
class Command(BaseCommand):
    help = "Run shipping reservation worker"

    def handle(self, *args, **options):
        connection, channel = build_consumer(
            queue_name="shipping.order.created",
            binding_keys=["order.created"],
        )

        def _process(_ch, _method, _props, body):
            payload = json.loads(body.decode("utf-8"))
            order_id = payload.get("order_id")
            should_fail = bool(payload.get("simulate_shipping_fail", False))
            time.sleep(5)  # simulate shipping processing delay

            if should_fail:
                Shipment.objects.update_or_create(order_id=order_id, defaults={"status": "FAILED"})
                publish_event("shipping.failed", {"order_id": order_id, "reason": "simulated shipping failure"})
                self.stdout.write(self.style.WARNING(f"Shipping failed for order={order_id}"))
                return

            Shipment.objects.update_or_create(order_id=order_id, defaults={"status": "RESERVED"})
            publish_event("shipping.reserved", {"order_id": order_id})
            self.stdout.write(self.style.SUCCESS(f"Shipping reserved for order={order_id}"))

        channel.basic_consume(
            queue="shipping.order.created",
            on_message_callback=lambda ch, method, props, body: (_process(ch, method, props, body), ch.basic_ack(method.delivery_tag)),
        )
        self.stdout.write(self.style.SUCCESS("Shipping worker started"))
        try:
            channel.start_consuming()
        finally:
            connection.close()
