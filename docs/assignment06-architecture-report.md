# Assignment 06 Architecture Justification

## ADDED-ASSIGNMENT06 Summary

This upgrade adds practical microservice techniques:

- JWT authentication service with token issuing/validation.
- Saga pattern with compensation for distributed order flow.
- RabbitMQ event bus for asynchronous service communication.
- API gateway enhancements: auth validation, logging, rate limiting.
- Observability baseline with health endpoints.
- Fault simulation and load testing assets.

## 1) JWT Authentication Service

Why:

- Centralized token generation and validation avoids duplicated auth logic in each service.
- API Gateway acts as policy enforcement point for all incoming traffic.

Trade-off:

- Auth service is a critical dependency. Gateway returns 503 when auth-service is unavailable.

## 2) Saga Pattern (Distributed Transaction)

Why:

- A normal ACID transaction cannot span order, payment, and shipping databases.
- Saga coordinates local transactions using events.

Flow:

1. order-service creates order with PENDING.
2. order-service publishes order.created.
3. pay-service reserves payment and emits payment.reserved or payment.failed.
4. ship-service reserves shipping and emits shipping.reserved or shipping.failed.
5. order-saga-worker confirms order when both reservations succeed.
6. On any failure, order becomes CANCELED (compensation transaction).

Compensation policy:

- Payment/Shipping failures are compensated by canceling order state.
- Compensation reason is persisted in order.compensation_reason.

## 3) Event Bus Choice

Chosen tool: RabbitMQ topic exchange (bookstore.events).

Why:

- Lightweight setup for assignment environment.
- Supports fan-out style event distribution with routing keys.
- Easy to run locally with Docker and inspect via management UI.

## 4) API Gateway Responsibilities

Implemented:

- Routing: existing page handlers call downstream services.
- Auth validation: JWTValidationMiddleware validates token by calling auth-service.
- Logging: RequestLoggingMiddleware logs method/path/status/latency.
- Rate limit: SimpleRateLimitMiddleware (120 requests/min/IP).

## 5) Observability

Implemented minimal endpoints:

- /health on gateway/auth/order/pay/ship.

Future extension:

- Add /metrics and scrape with Prometheus.
- Centralize logs into ELK/Loki.

## 6) Fault Simulation

Supported flags on order creation:

- simulate_payment_fail
- simulate_shipping_fail

Purpose:

- Validate compensation behavior and recovery scenarios.

## 7) Load Testing

Provided script:

- load-test/k6-order-saga.js

How to run:

1. Install k6.
2. Start stack with docker compose up --build.
3. Run: k6 run load-test/k6-order-saga.js

## 8) Persistence Note

Because SQLite is used, each service API and its worker share one Docker volume and SQLITE_DB_PATH.
This is required so workers can read/write the same state as the corresponding API service.
