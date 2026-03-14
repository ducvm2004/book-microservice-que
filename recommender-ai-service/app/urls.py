from django.urls import path
from .views import get_recommendation

urlpatterns = [
    path('recommendations/<int:customer_id>/', get_recommendation),
]
