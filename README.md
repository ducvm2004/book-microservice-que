# Bookstore Microservice - Docker Guide

## Prerequisites

- Docker Desktop is running
- Docker Compose CLI is available (`docker compose version`)

## Run all services

```bash
docker compose up --build
```

## Run all services in detached mode

```bash
docker compose up --build -d
```

## Stop all services

```bash
docker compose down
```

## Rebuild images only

```bash
docker compose build
```

## Rebuild and restart a single service

```bash
docker compose up --build -d book-service
```

## View logs

```bash
docker compose logs -f
```

## View logs for one service

```bash
docker compose logs -f order-service
```

## Check running containers

```bash
docker compose ps
```

## Quick API checks

- API Gateway: http://localhost:8000/books/
- Customer Service: http://localhost:8001/customers/
- Book Service: http://localhost:8002/books/
- Cart Service: http://localhost:8003/carts/
- Order Service: http://localhost:8004/orders/
- Pay Service: http://localhost:8005/payments/
- Ship Service: http://localhost:8006/shipments/
- Comment Rate Service: http://localhost:8007/ratings/
- Recommender AI Service: http://localhost:8008/recommendations/1/

## Common issue

If you see daemon/pipe errors on Windows (for example `dockerDesktopLinuxEngine`), start Docker Desktop first, then run:

```bash
docker info
```

If `Server` information appears, run compose commands again.

## Assignment 06 Upgrade Notes

### ADDED-ASSIGNMENT06: JWT Authentication Service

- New service: `auth-service`
- APIs:
  - `POST /auth/login/` -> generate JWT
  - `POST /auth/validate/` -> validate JWT
  - `GET /health/` -> health check

Gateway integration:

- Login now requests JWT from `auth-service` and stores it in session.
- Gateway middleware validates JWT on protected routes.

### ADDED-ASSIGNMENT06: Saga Pattern + Compensation

Order flow is now asynchronous:

1. `order-service` creates order with `PENDING`
2. publish event `order.created`
3. `pay-service` reserves payment -> emits `payment.reserved` or `payment.failed`
4. `ship-service` reserves shipping -> emits `shipping.reserved` or `shipping.failed`
5. `order-saga-worker` confirms order when both reserved
6. on any failure -> compensation by setting order `CANCELED`

Fault simulation:

- `simulate_payment_fail=true`
- `simulate_shipping_fail=true`
- ADDED-ASSIGNMENT06 update: simulation controls are disabled in Gateway UI to avoid accidental failures.

### ADDED-ASSIGNMENT06: Event Bus (RabbitMQ)

- RabbitMQ container added (`5672`, management UI `15672`)
- Exchange: `bookstore.events` (topic)
- Workers:
  - `order-saga-worker`
  - `pay-event-worker`
  - `ship-event-worker`

### ADDED-ASSIGNMENT06: API Gateway Responsibilities

- Routing: existing gateway route handlers
- Auth validation: JWTValidationMiddleware
- Logging: RequestLoggingMiddleware
- Rate limit: SimpleRateLimitMiddleware (120 req/min/IP)

### ADDED-ASSIGNMENT06: Observability

Health endpoints:

- Gateway: `http://localhost:8000/health/`
- Auth: `http://localhost:8010/health/`
- Order: `http://localhost:8004/health/`
- Pay: `http://localhost:8005/health/`
- Ship: `http://localhost:8006/health/`

### ADDED-ASSIGNMENT06: Advanced Deliverables

- Load test script: `load-test/k6-order-saga.js`
- Architecture report: `docs/assignment06-architecture-report.md`
