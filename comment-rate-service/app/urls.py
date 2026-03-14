from django.urls import path
from .views import RatingListCreate

urlpatterns = [
    path('ratings/', RatingListCreate.as_view()),
]
