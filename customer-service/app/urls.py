from django.urls import path
from .views import CustomerListCreate

urlpatterns = [
    path('customers/', CustomerListCreate.as_view()),
]
