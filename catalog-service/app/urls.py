from django.urls import path
from .views import CategoryListCreate

urlpatterns = [
    path('categories/', CategoryListCreate.as_view()),
]
