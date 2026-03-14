from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Rating
from .serializers import RatingSerializer


class RatingListCreate(APIView):
    def get(self, request):
        ratings = Rating.objects.all()
        return Response(RatingSerializer(ratings, many=True).data)

    def post(self, request):
        serializer = RatingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
