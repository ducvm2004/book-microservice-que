from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Staff
from .serializers import StaffSerializer


class StaffListCreate(APIView):
    def get(self, request):
        staff = Staff.objects.all()
        return Response(StaffSerializer(staff, many=True).data)

    def post(self, request):
        serializer = StaffSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
