from django.urls import path
from .views import ManagerListCreate

urlpatterns = [
    path('managers/', ManagerListCreate.as_view()),
]
