# API Gateway & Rate Limiter

A production-style API Gateway built with FastAPI, simulating how real companies handle authentication, rate limiting, logging, and traffic routing at scale — not a basic CRUD app.

**Live demo:** https://api-gateway-project-a8it.onrender.com/docs
**Health check:** https://api-gateway-project-a8it.onrender.com/health

---

## What this project demonstrates

Most portfolio backend projects stop at CRUD. This one is built around the infrastructure concerns that actually matter once an API has real users:

- Who is allowed to call this API, and how do we prove it (JWT *and* API keys)
- How do we stop any one user from overwhelming the system (Redis-backed sliding window rate limiting)
- How do we debug production issues after the fact (structured request logging)
- How do we understand usage patterns (analytics built on that log data)
- How do we route traffic to different backend services from one entry point (simulated microservice routing)
- How do we gate features by subscription tier (plan-based access control)
- How do we harden the surface area against abuse (input validation, security headers, CORS, brute-force protection)
- How do we fail predictably (consistent error envelopes, health checks)
- How do we prove it all actually works (automated test suite)

---

## Architecture

```
Client
  │
  ▼
API Gateway
  ├── Auth middleware   (JWT or X-API-Key)
  ├── Rate limiter       (Redis sliding window, per-plan)
  └── Request logging    (every request, success or failure)
  │
  ▼
Simulated microservices
  ├── User service
  ├── Product service
  └── Order service
  │
  ▼
PostgreSQL              Redis
(users, keys,            (rate limit
 products, orders,        counters)
 logs)
```

Every request passes through the same auth → rate-limit → logging pipeline regardless of which downstream "service" it's headed to — this is the core value proposition of a gateway: cross-cutting concerns handled once, centrally, instead of duplicated per service.

---

## Features

### Authentication
- Register / login with bcrypt-hashed passwords
- JWT access tokens with expiry
- `GET /me` protected route

### API key management
- Users can generate long-lived API keys (`sk_live_...`) for machine-to-machine access
- Raw key shown exactly once at creation; only a bcrypt hash is stored afterward
- Soft delete (disable) preserves an audit trail instead of destroying records

### Unified authentication middleware
- A single dependency accepts *either* a JWT (`Authorization: Bearer`) or an API key (`X-API-Key`)
- API key lookups are prefix-filtered before the (deliberately slow) bcrypt comparison, so verification stays fast even as the key table grows

### Rate limiting
- Redis-backed **sliding window** algorithm (not fixed window) — avoids the boundary-burst problem where a fixed window resets and lets a user send double their limit across a window edge
- Limits vary by plan: Free (100/hr), Premium (5,000/hr), Enterprise (unlimited)
- Returns `429 Too Many Requests` with a clear message when exceeded
- Login endpoint has a separate, IP-based rate limit to prevent credential brute-forcing

### Request logging
- Every request is logged — including unauthenticated and failed ones, since that's often the most security-relevant traffic
- Captures user, endpoint, method, IP, status code, response time, timestamp
- Implemented as middleware (not a per-route dependency), so no future route can accidentally skip it

### Analytics
- `GET /api/v1/analytics/overview` — total requests, requests today, average response time, failure rate, success rate
- `GET /api/v1/analytics/top-endpoints` — most-hit endpoints
- `GET /api/v1/analytics/top-users` — most active users
- All aggregation happens in SQL (not pulled into Python), since pushing aggregation down to the database is the pattern that scales

### Simulated microservice routing
- `/gateway/users`, `/gateway/products`, `/gateway/orders` — each a cleanly separated router, as if it could become an independently deployed service with minimal changes
- Real, DB-backed models (not in-memory placeholders)

### User plans
- Free / Premium / Enterprise tiers, centrally defined
- Plans control both rate limits *and* feature access (`/premium-insights` demonstrates a plan-gated route returning `403` for insufficient tier)

### Security
- Field-level input validation (e.g. price must be positive, names can't be empty, passwords have a minimum length)
- Global security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`)
- Explicit CORS configuration
- IP-based rate limiting on login to blunt brute-force attempts

### Consistent error handling
- Every error — `HTTPException`, validation errors, and unhandled exceptions — is normalized into one JSON shape:
```json
{"success": false, "error": {"code": 404, "message": "Product not found"}}
```
- Unhandled exceptions are logged server-side with full detail but never leak a raw traceback to the client

### Health check
- `GET /health` actively verifies Postgres and Redis connectivity, not just a hardcoded "ok"

### Testing
- 17 automated tests (pytest + FastAPI's `TestClient`) covering auth, API keys, rate limiting, and gateway routes

---

## Tech stack

Python · FastAPI · PostgreSQL · SQLAlchemy · Redis · JWT (`python-jose`) · bcrypt · Docker · pytest

## Infrastructure

- **Containerized** with Docker and `docker-compose` (app + Postgres + Redis run together with one command)
- **Deployed** on Render (app + Redis) with Neon (managed Postgres)

---

## Running locally

### With Docker (recommended)

```bash
git clone <this-repo-url>
cd api_gateway
docker-compose up --build
```

The app will be available at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

### Without Docker

Requires Python 3.12+, a running PostgreSQL instance, and a running Redis instance.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# set DATABASE_URL, REDIS_URL, SECRET_KEY in a .env file

uvicorn app.main:app --reload
```

## Running tests

```bash
pytest -v
```

---

## Key design decisions

**Why Redis for rate limiting, but Postgres for logs?**
Rate limiting needs extremely fast, short-lived, high-frequency counters — Redis is in-memory with native `TTL` and atomic increment support, which Postgres isn't built for at that access pattern. Logs, by contrast, are durable and need to be queried/aggregated later — exactly what Postgres is designed for.

**Why sliding window instead of fixed window rate limiting?**
A fixed window (e.g. "100 requests per clock-minute") lets a user send 100 requests at the last second of one window and another 100 at the first second of the next — 200 requests in roughly two seconds. A sliding window (implemented here with a Redis sorted set) evaluates "the last N seconds from right now," continuously, closing that loophole.

**Why soft delete for API keys instead of hard delete?**
Mirrors how real systems behave (revoked keys still show up as inactive in Stripe/GitHub dashboards) and preserves an audit trail rather than destroying history.

**Why a separate `X-API-Key` header instead of reusing `Authorization: Bearer` for API keys?**
Keeps the two authentication mechanisms unambiguous — middleware can immediately tell which type of credential it's dealing with rather than trying to infer it from a token's shape.

---

## Project status

All 12 core modules complete: authentication, API key management, unified middleware, rate limiting, logging, analytics, routing, plans, security hardening, error handling, health checks, and automated testing.