from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def get_recommendation(request, customer_id):
    return Response({
        "recommended_books": [1, 3, 5]
    })
