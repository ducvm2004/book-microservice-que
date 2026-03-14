from django.urls import path
from .views import OrderListCreate

urlpatterns = [
    path('orders/', OrderListCreate.as_view()),
]
