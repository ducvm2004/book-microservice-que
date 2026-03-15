from django.urls import path
from .views import HealthView, PaymentDetail, PaymentListCreate

urlpatterns = [
    path('payments/', PaymentListCreate.as_view()),
    path('payments/<int:pk>/', PaymentDetail.as_view()),
    path('health/', HealthView.as_view()),
]
