from django.urls import path
from .views import BookListCreate, BookRetrieve

urlpatterns = [
    path('books/', BookListCreate.as_view()),
    path('books/<int:pk>/', BookRetrieve.as_view()),
]
