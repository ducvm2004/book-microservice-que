from django.urls import path
from .views import HealthView, LoginView, ValidateView

urlpatterns = [
    path("auth/login/", LoginView.as_view()),
    path("auth/validate/", ValidateView.as_view()),
    path("health/", HealthView.as_view()),
]
