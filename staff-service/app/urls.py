from django.urls import path
from .views import StaffListCreate

urlpatterns = [
    path('staffs/', StaffListCreate.as_view()),
]
