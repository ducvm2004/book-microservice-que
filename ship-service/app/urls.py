from django.urls import path
from .views import ShipmentListCreate

urlpatterns = [
    path('shipments/', ShipmentListCreate.as_view()),
]
