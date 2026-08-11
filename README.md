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

## Security

### Authentication
Two methods are supported and unified through a single dependency (`get_current_identity`):
- **JWT** (`Authorization: Bearer <token>`) — for human/browser sessions. Signature, expiration, and algorithm are all verified on every request; the algorithm is pinned via configuration, preventing algorithm-confusion attacks.
- **API keys** (`X-API-Key: <key>`) — for machine-to-machine access. Keys are bcrypt-hashed at rest; the raw key is shown exactly once, at creation, and never stored or re-exposed afterward.

Routes intended only for human dashboard use (e.g. `/me`) accept JWT only. Gateway/data routes accept either method via `get_current_identity`, since both resolve to the same underlying `user_id`.

### Credential Handling
- Passwords and API keys are hashed with bcrypt; plaintext is never stored.
- Authentication headers (`Authorization`, `X-API-Key`) are never written to logs — the logging middleware only extracts a resolved `user_id`, never the raw header value.
- Login failures return a generic "incorrect email or password" message regardless of whether the email exists, preventing user enumeration.

### Rate Limiting & Brute-Force Protection
General API rate limiting (per-user, sliding window) and login brute-force protection (per-IP) use separate Redis key namespaces (`ratelimit:user:*` vs `ratelimit:login:*`) and do not interfere with each other.

### CORS
Allowed origins are environment-configurable (`CORS_ALLOWED_ORIGINS`), not hardcoded, so development and production can use different values without a code change.

### Input Validation
Request bodies are validated via Pydantic (field types, length constraints, numeric bounds). All database access goes through SQLAlchemy's ORM/parameterized queries — no raw SQL string construction from user input exists anywhere in the codebase.

### Authorization Boundaries
Authenticated identity is always derived from the validated JWT/API key, never from client-supplied request data. Extra fields in a request body (e.g. an attempted `user_id` override) are ignored by the Pydantic schema and have no effect — verified by automated test.

### Secret Management
All secrets (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`) are environment-variable-driven, documented in `.env.example` with placeholder values only. `.env` is gitignored and confirmed never committed to this repository's history.

### Authentication Failure Behavior
All authentication/authorization failures return the centralized error envelope with a `request_id` for correlation, and appropriate status codes (`401` for missing/invalid credentials, `403` for insufficient plan/permissions, `429` for rate limiting).

**Not implemented (explicitly out of scope for this stage):** refresh tokens, OAuth providers, RBAC, MFA, SSO.

### Consistent error handling
- Every error — `HTTPException`, validation errors, and unhandled exceptions — is normalized into one JSON shape:
```json
{"success": false, "error": {"code": 404, "message": "Product not found"}}
```
- Unhandled exceptions are logged server-side with full detail but never leak a raw traceback to the client

## Production reliability features (Day 1 upgrade)

### Configuration
All configuration — database, Redis, JWT secrets, rate-limit thresholds, timeouts — is centralized in `app/core/config.py` and driven entirely by environment variables (see `.env.example`). Nothing is hardcoded in source.

### Request IDs
Every request is assigned a unique `X-Request-ID` (or the caller's own, if provided), returned in the response header and threaded through every log line and error response for that request — enabling full request tracing without a distributed tracing system.

### Structured logging
Requests are logged as structured JSON (timestamp, level, request_id, method, path, status_code, response_time, user_id, and error details when applicable), written to stdout — parseable by any standard log viewer without adopting an external observability platform.

### Health check
`GET /health` — liveness only. Confirms the FastAPI process is running; performs no dependency checks and stays fast.

### Readiness check
`GET /ready` — confirms PostgreSQL and Redis are reachable. Returns `503` if either dependency is unavailable, so traffic can be withheld without restarting a healthy process.

### Error handling
All errors (`HTTPException`, validation errors, unhandled exceptions) return a consistent envelope:
```json
{"success": false, "error": {"code": 404, "message": "...", "request_id": "..."}}
```
Unhandled exceptions are logged with full detail server-side but never expose internals to the client.

### Redis failure strategy
Rate limiting fails **open**: if Redis is unreachable, the failure is logged (with request ID) and the request is allowed to continue, rather than taking the entire API down over a secondary feature.

### Downstream timeout handling
Outbound calls to external/downstream services use an explicit, configurable timeout (`DOWNSTREAM_TIMEOUT_SECONDS`). Timeouts return `504 Gateway Timeout`; connection failures return `502 Bad Gateway` — both logged with request ID correlation.

### Testing
27 automated tests (pytest), including 9 new reliability tests covering request IDs, health/readiness, error response structure, Redis fail-open behavior, and downstream timeout handling. External dependencies (Redis failures, slow downstream calls) are mocked for deterministic, fast test runs.

## Rate Limiting

### Algorithm: Sliding Window
The rate limiter uses a sliding window (not fixed window), implemented with a Redis sorted set per client. A fixed window allows a client to send up to 2x their limit across a window boundary (e.g., 100 requests in the last second of one window, another 100 in the first second of the next). A sliding window evaluates "the last N seconds from right now," continuously, closing that gap.

### Redis Data Structure
Each client's request history is stored in a Redis sorted set, where the score is the request timestamp (Unix seconds) and the member is a unique per-request identifier.

### Key Design

Examples:
- `ratelimit:user:free:42` — per-user limiter, free plan
- `ratelimit:login:ip:203.0.113.5` — login attempt limiter, keyed by IP

No PII (email, tokens) is embedded in Redis keys — only numeric user IDs or IP addresses.

### Atomicity
The full sliding-window decision (remove expired entries, count, decide, record, set expiry) executes as a single Redis Lua script (`EVAL`), guaranteeing atomicity from Redis's perspective. This was a deliberate fix for a real race condition in the prior implementation, where the same logic ran as 4 separate Redis round-trips — under concurrent load, two requests could both read the count before either wrote their entry, allowing the limit to be exceeded. Verified fixed via automated concurrency tests (`tests/test_rate_limiter_concurrency.py`) and a load benchmark showing exactly 100/100 allowed under a 100-request limit with 200 concurrent requests, zero overcounting.

### Client Identity
- **Per-user rate limiting**: keyed by `user_id`, resolved identically whether the request used a JWT or an API key — both credential types for the same user share one bucket, since the limit is meant to apply to the user, not the credential mechanism.
- **Login attempt limiting**: keyed by IP address, since no authenticated identity exists yet at login time. This is a separate, stricter limiter protecting against credential-stuffing/brute-force attempts.

### Plan-Based Limits
Defined centrally in `app/core/plans.py`:
| Plan | Limit |
|---|---|
| Free | 100 requests / hour |
| Premium | 5,000 requests / hour |
| Enterprise | Unlimited (no rate-limit headers issued) |

The window size is configurable via `RATE_LIMIT_WINDOW_SECONDS`.

### Redis Failure Strategy
Fails **open**: if Redis is unreachable or times out (2s socket timeout), the failure is logged with the request's correlation ID, and the request is allowed to proceed rather than blocking all traffic over a secondary feature's outage.

### 429 Response
```json
{"success": false, "error": {"code": 429, "message": "Rate limit exceeded: ...", "request_id": "..."}}
```
Includes a `Retry-After` header with an accurate seconds-until-reset value, calculated from the oldest entry still inside the window.

### Rate-Limit Headers
Returned on every rate-limited (non-enterprise) response:
- `X-RateLimit-Limit` — the plan's request ceiling
- `X-RateLimit-Remaining` — requests left in the current window
- `X-RateLimit-Reset` — Unix timestamp when the window resets

Omitted entirely for unlimited (enterprise) plans and during Redis fail-open, rather than showing misleading values.

### Concurrency Considerations
The atomic Lua script prevents race conditions *within a single Redis instance*. This implementation does not provide distributed guarantees across multiple Redis instances/clusters — it assumes a single Redis deployment, which is the current architecture.

### Benchmark (measured, local dev environment)
Conditions: 200 total requests, 20 concurrent clients, 100 req/hour limit, single-process Uvicorn dev server (`--reload`), local Postgres + Redis.

| Metric | Result |
|---|---|
| Requests/sec | 73.65 |
| Average latency | 263.83ms |
| p95 latency | 406.85ms |
| Allowed | 100 |
| Rejected (429) | 100 |
| Errors | 0 |

These figures reflect a local development environment, not a tuned production deployment (single worker process, dev-mode reload enabled). Re-run `benchmarks/rate_limit_bench.py` to reproduce.
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