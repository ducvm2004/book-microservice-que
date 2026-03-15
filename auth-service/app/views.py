from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


def _build_token(username, role):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.JWT_EXPIRE_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ADDED-ASSIGNMENT06: issue JWT token for API Gateway login flow.
class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        role = (request.data.get("role") or "customer").strip().lower()

        if not username:
            return Response({"detail": "username is required"}, status=status.HTTP_400_BAD_REQUEST)
        if role not in {"customer", "staff"}:
            return Response({"detail": "invalid role"}, status=status.HTTP_400_BAD_REQUEST)

        token = _build_token(username=username, role=role)
        return Response({"access_token": token, "token_type": "Bearer", "expires_in": settings.JWT_EXPIRE_SECONDS})


# ADDED-ASSIGNMENT06: allow API Gateway to validate JWT on every protected request.
class ValidateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"valid": False, "detail": "token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return Response({"valid": True, "payload": payload})
        except jwt.ExpiredSignatureError:
            return Response({"valid": False, "detail": "token expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.PyJWTError:
            return Response({"valid": False, "detail": "token invalid"}, status=status.HTTP_401_UNAUTHORIZED)


# ADDED-ASSIGNMENT06: basic observability health endpoint.
class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "auth-service"})
