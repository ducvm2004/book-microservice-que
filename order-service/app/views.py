from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from .serializers import OrderSerializer
from .event_bus import publish_event


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class OrderListCreate(APIView):
    def get(self, request):
        orders = Order.objects.all()
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        serializer = OrderSerializer(data={"customer_id": request.data.get("customer_id")})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # ADDED-ASSIGNMENT06: initialize distributed transaction in PENDING state.
        order = serializer.save(
            status="PENDING",
            payment_reserved=False,
            shipping_reserved=False,
            compensation_reason="",
        )

        saga_payload = {
            "order_id": order.id,
            "customer_id": order.customer_id,
            # ADDED-ASSIGNMENT06: fault simulation controls for grading requirements.
            "simulate_payment_fail": _as_bool(request.data.get("simulate_payment_fail", False)),
            "simulate_shipping_fail": _as_bool(request.data.get("simulate_shipping_fail", False)),
        }
        publish_event("order.created", saga_payload)

        return Response(OrderSerializer(order).data, status=status.HTTP_202_ACCEPTED)


class OrderDetail(APIView):
    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(OrderSerializer(order).data)


# ADDED-ASSIGNMENT06: basic observability health endpoint.
class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "order-service"})
