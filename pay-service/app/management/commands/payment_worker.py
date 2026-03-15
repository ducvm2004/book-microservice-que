import json
import time

from django.core.management.base import BaseCommand

from app.event_bus import build_consumer, publish_event
from app.models import Payment


# ADDED-ASSIGNMENT06: payment participant in Saga reserve step.
class Command(BaseCommand):
    help = "Run payment reservation worker"

    def handle(self, *args, **options):
        connection, channel = build_consumer(
            queue_name="payment.order.created",
            binding_keys=["order.created"],
        )

        def _process(_ch, _method, _props, body):
            payload = json.loads(body.decode("utf-8"))
            order_id = payload.get("order_id")
            should_fail = bool(payload.get("simulate_payment_fail", False))
            time.sleep(5)  # simulate payment processing delay

            if should_fail:
                Payment.objects.update_or_create(order_id=order_id, defaults={"status": "FAILED"})
                publish_event("payment.failed", {"order_id": order_id, "reason": "simulated payment failure"})
                self.stdout.write(self.style.WARNING(f"Payment failed for order={order_id}"))
                return

            Payment.objects.update_or_create(order_id=order_id, defaults={"status": "RESERVED"})
            publish_event("payment.reserved", {"order_id": order_id})
            self.stdout.write(self.style.SUCCESS(f"Payment reserved for order={order_id}"))

        channel.basic_consume(
            queue="payment.order.created",
            on_message_callback=lambda ch, method, props, body: (_process(ch, method, props, body), ch.basic_ack(method.delivery_tag)),
        )
        self.stdout.write(self.style.SUCCESS("Payment worker started"))
        try:
            channel.start_consuming()
        finally:
            connection.close()
