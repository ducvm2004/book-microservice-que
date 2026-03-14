from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Shipment
from .serializers import ShipmentSerializer


class ShipmentListCreate(APIView):
    def get(self, request):
        shipments = Shipment.objects.all()
        return Response(ShipmentSerializer(shipments, many=True).data)

    def post(self, request):
        serializer = ShipmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
