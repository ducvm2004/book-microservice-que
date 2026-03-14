from django.urls import path
from .views import PaymentListCreate

urlpatterns = [
    path('payments/', PaymentListCreate.as_view()),
]
