from django.urls import path
from .views import PaymentDetail, PaymentListCreate

urlpatterns = [
    path('payments/', PaymentListCreate.as_view()),
    path('payments/<int:pk>/', PaymentDetail.as_view()),
]
