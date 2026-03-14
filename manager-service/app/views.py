from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Manager
from .serializers import ManagerSerializer


class ManagerListCreate(APIView):
    def get(self, request):
        managers = Manager.objects.all()
        return Response(ManagerSerializer(managers, many=True).data)

    def post(self, request):
        serializer = ManagerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
