import threading
import time

import requests
from django.http import JsonResponse
from django.shortcuts import redirect


# ADDED-ASSIGNMENT06: simple in-memory rate limiter for API Gateway.
class SimpleRateLimitMiddleware:
    _lock = threading.Lock()
    _hits = {}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith("/admin") or path.startswith("/health") or path.startswith("/static"):
            return self.get_response(request)

        now = int(time.time())
        window = now // 60
        ip = request.META.get("REMOTE_ADDR", "unknown")
        key = (ip, window)

        with self._lock:
            self._hits[key] = self._hits.get(key, 0) + 1
            current = self._hits[key]

            # Keep memory bounded by dropping old windows.
            stale_keys = [k for k in self._hits if k[1] < window - 1]
            for stale_key in stale_keys:
                self._hits.pop(stale_key, None)

        if current > 120:
            return JsonResponse({"detail": "rate limit exceeded"}, status=429)

        return self.get_response(request)


# ADDED-ASSIGNMENT06: request logging middleware for auditability.
class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start) * 1000)
        print(f"[GATEWAY] {request.method} {request.path} status={response.status_code} duration_ms={duration_ms}")
        return response


# ADDED-ASSIGNMENT06: validate JWT with auth-service before forwarding to protected views.
class JWTValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auth_service_validate_url = "http://auth-service:8000/auth/validate/"

    def __call__(self, request):
        path = request.path
        exempt_prefixes = ["/login", "/logout", "/admin", "/health", "/static"]
        if any(path.startswith(prefix) for prefix in exempt_prefixes):
            return self.get_response(request)

        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.session.get("jwt_token")

        if not token:
            return redirect("login")

        try:
            response = requests.post(self.auth_service_validate_url, json={"token": token}, timeout=3)
            if response.status_code != 200 or not response.json().get("valid"):
                request.session.pop("jwt_token", None)
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": "invalid token"}, status=401)
                return redirect("login")
            request.jwt_payload = response.json().get("payload", {})
        except requests.RequestException:
            return JsonResponse({"detail": "auth service unavailable"}, status=503)

        return self.get_response(request)
