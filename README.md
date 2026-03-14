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
