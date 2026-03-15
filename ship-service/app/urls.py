from django.urls import path
from .views import HealthView, ShipmentListCreate

urlpatterns = [
    path('shipments/', ShipmentListCreate.as_view()),
    path('health/', HealthView.as_view()),
]
