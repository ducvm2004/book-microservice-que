from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from .serializers import OrderSerializer
import requests


PAY_SERVICE_URL = "http://pay-service:8000"
SHIP_SERVICE_URL = "http://ship-service:8000"


class OrderListCreate(APIView):
    def get(self, request):
        orders = Order.objects.all()
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        serializer = OrderSerializer(data={"customer_id": request.data.get("customer_id")})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order = serializer.save(status='PENDING')

        payment_status = request.data.get("payment_status", "PAID")
        shipment_status = request.data.get("shipment_status", "SHIPPED")

        allowed_payment_status = {"PAID", "PENDING", "FAILED"}
        allowed_shipment_status = {"SHIPPED", "PROCESSING", "PENDING"}
        if payment_status not in allowed_payment_status:
            order.delete()
            return Response({"payment_status": "Invalid payment status"}, status=status.HTTP_400_BAD_REQUEST)
        if shipment_status not in allowed_shipment_status:
            order.delete()
            return Response({"shipment_status": "Invalid shipment status"}, status=status.HTTP_400_BAD_REQUEST)

        pay_resp = requests.post(
            f"{PAY_SERVICE_URL}/payments/",
            json={"order_id": order.id, "status": payment_status},
            timeout=5,
        )
        ship_resp = requests.post(
            f"{SHIP_SERVICE_URL}/shipments/",
            json={"order_id": order.id, "status": shipment_status},
            timeout=5,
        )

        if pay_resp.status_code not in [200, 201] or ship_resp.status_code not in [200, 201]:
            order.status = 'FAILED'
        elif payment_status == 'PAID' and shipment_status == 'SHIPPED':
            order.status = 'COMPLETED'
        elif payment_status == 'FAILED':
            order.status = 'FAILED'
        else:
            order.status = 'PROCESSING'

        order.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
