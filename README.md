# API Gateway & Rate Limiter

A production-style API Gateway built with FastAPI — simulating how real companies handle authentication, rate limiting, logging, and traffic routing at the edge of their systems. Built incrementally as a 12-module MVP, then hardened across four upgrade passes (reliability, rate-limiter concurrency, security, API/database design).

**Live demo:** https://api-gateway-project-a8it.onrender.com/docs
**Health check:** https://api-gateway-project-a8it.onrender.com/health

---

## What This Project Demonstrates

Most portfolio backend projects stop at CRUD. This one is built around the infrastructure concerns that matter once an API has real traffic:

- Authenticating callers two different ways (JWT for humans, API keys for machines) through one unified gateway checkpoint
- Stopping any one client from overwhelming the system, correctly, even under real concurrent load
- Recording enough structured data to actually debug a production incident after the fact
- Routing traffic to multiple simulated backend services from a single entry point
- Gating features by subscription tier, not just rate limits
- Failing gracefully when a dependency (Redis) goes down, instead of taking the whole API with it
- Auditing and hardening its own auth, CORS, and query performance rather than assuming they're fine

---

## Architecture

```
Client
  │
  ▼
API Gateway
  ├── Request ID middleware   (X-Request-ID generated/preserved)
  ├── Auth middleware         (JWT or X-API-Key)
  ├── Rate limiter            (Redis, atomic sliding window, per-plan)
  └── Structured logging      (every request, success or failure)
  │
  ▼
Simulated microservices
  ├── User service
  ├── Product service
  └── Order service
  │
  ▼
PostgreSQL                 Redis
(users, keys,               (rate limit
 products, orders,           counters)
 logs)
```

Every request passes through the same auth → rate-limit → logging pipeline regardless of which downstream "service" it's headed to. That's the core value of a gateway: cross-cutting concerns handled once, centrally, instead of duplicated per service.

---

## Tech Stack

Python · FastAPI · PostgreSQL · SQLAlchemy · Alembic · Redis · JWT (`python-jose`) · bcrypt · Docker · pytest

**Infrastructure:** Dockerized with `docker-compose` (app + Postgres + Redis run together). Deployed on Render (app + Redis) with Neon (managed Postgres).

---

## Core Features

### Authentication
- Register / login with bcrypt-hashed passwords (never stored or logged in plaintext)
- JWT access tokens — signature, expiration, and a pinned algorithm whitelist all verified on every request
- `GET /me` protected route

### API Key Management
- Long-lived keys (`sk_live_...`) for machine-to-machine access, generated per user
- Raw key shown exactly once at creation; only a bcrypt hash is stored afterward
- Soft delete (`active` flag + `revoked_at` timestamp) — preserves an audit trail instead of destroying records, mirroring how Stripe/GitHub handle key revocation

### Unified Authentication Middleware
- One dependency (`get_current_identity`) accepts either a JWT or an API key
- API key lookups filter by a fast, **indexed** `prefix` column before running the deliberately-slow bcrypt comparison — keeps auth fast even as the key table grows

### Rate Limiting
- Redis-backed **sliding window** (not fixed window — avoids the boundary-burst flaw where a client could send double their limit across a window edge)
- The full check-and-record sequence executes as a single **atomic Redis Lua script** — fixes a real race condition where concurrent requests could exceed the configured limit
- Limits vary by plan: Free (100/hr), Premium (5,000/hr), Enterprise (unlimited)
- `429` responses include an accurate `Retry-After` header and `X-RateLimit-Limit/Remaining/Reset` headers on every response
- Fails **open** on Redis outages — logs the failure loudly, lets the request through, rather than taking the whole API down over a secondary feature
- A separate, IP-based limiter protects the login endpoint from brute-force attempts, independent of the main per-user limiter

### Request Logging & Analytics
- Every request is logged — including unauthenticated and failed ones, since that's often the most security-relevant traffic
- Structured JSON logs (timestamp, level, `request_id`, method, path, status, response time, user) to stdout, plus a database-backed log table
- `GET /api/v1/analytics/overview`, `/top-endpoints`, `/top-users` — all SQL-aggregated, not pulled into Python

### Simulated Microservice Routing
- `/gateway/users`, `/gateway/products`, `/gateway/orders` — separate router modules, each backed by real database models, structured as if they could become independently deployed services

### User Plans
- Free / Premium / Enterprise, centrally defined
- Plans control both rate limits and feature access (a `/premium-insights` route demonstrates `403` gating by tier)

### Security
- Field-level input validation (positive prices, non-empty names, minimum password length)
- Global security headers, environment-configurable CORS (no hardcoded origins)
- Authenticated identity is always derived from the validated credential, never from client-supplied request data
- Full secret audit: no credentials in source, README, Docker files, logs, or git history

### Reliability
- `X-Request-ID` on every request, threaded through logs and error responses for full traceability
- `GET /health` (liveness only) and `GET /ready` (checks Postgres + Redis, returns `503` if either is down) — kept intentionally separate
- Centralized error envelope for every failure type, including `request_id` for correlation, never leaking internals
- Explicit, configurable timeouts on both Redis and outbound HTTP calls

### API Design & Database Performance
- Pagination (`limit`/`offset`, capped at 100) on all collection endpoints — no unbounded queries
- Whitelisted sort fields (`Literal` type) — no path for arbitrary input to reach query construction
- Schema migrations managed with Alembic, not manual `ALTER TABLE`
- Indexed `api_keys.prefix`, the busiest lookup column in the auth path

### Testing
- 43 automated tests (pytest + FastAPI `TestClient`): auth, API keys, rate limiting (including real concurrency tests with actual threads), Redis integration, security boundaries, pagination

---

## API Design

**Authentication:** JWT (`Authorization: Bearer <token>`) or API key (`X-API-Key: <key>`).

**Status codes:** `200` success · `201` resource created · `204` deleted (no body) · `401` auth failure · `403` plan-gated feature · `404` not found · `422` validation · `429` rate limited · `502`/`504` downstream failure/timeout · `500` unexpected (logged server-side only, never exposed).

**Pagination:** `GET /gateway/products`, `/gateway/orders`, `/api/v1/api-keys` accept `limit` (1–100, default 20) and `offset` (default 0). Response shape: `{"total", "limit", "offset", "items": [...]}`. All paginated queries use an explicit `ORDER BY` — required for consistent results across pages, since PostgreSQL doesn't guarantee row order without one.

**Filtering & sorting:** `GET /gateway/products` accepts `sort_by` (whitelisted: `id`, `name`, `price`, `created_at`), validated via a `Literal` type — any other value is rejected with `422` before it can reach query construction.

**Error format:** `{"success": false, "error": {"code", "message", "request_id"}}`, consistent across every failure type.

**Request IDs:** every response includes `X-Request-ID`, correlating to structured server-side logs.

---

## Database Design

**Core tables:** `users`, `api_keys`, `products`, `orders`, `request_logs`.

**Key relationships:** `api_keys.user_id → users.id`, `orders.user_id → users.id`, `orders.product_id → products.id` — all enforced as foreign keys.

**Indexes:**
- `users.email` — unique index, backs every login lookup
- `api_keys.prefix` — index added via Alembic migration, since this column is queried on every API-key-authenticated request. At current data volume (~100 rows), PostgreSQL's query planner still chooses a sequential scan over the index (confirmed via `EXPLAIN ANALYZE`) — sequential scan is genuinely faster on tables this small, so this is correct planner behavior, not a failed optimization. The index is a forward-looking scalability improvement; no performance gain is claimed at current scale.

**Transaction strategy:** each write follows SQLAlchemy's standard per-request pattern (`add` → `commit` → `refresh`), committing atomically per operation. No long-lived or manually-managed transactions exist.

**Connection pooling:** `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True` — raised from SQLAlchemy's defaults after concurrency testing exhausted the original pool (every request needs a connection for both auth and logging).

**Known limitation — idempotency:** POST endpoints (e.g. order creation) are not currently idempotent — a retried request could theoretically create a duplicate resource. No client-facing retry behavior currently exists that makes this a live problem, so it hasn't been implemented; idempotency keys are a documented future improvement, not built today.

---

## Rate Limiting

**Algorithm:** sliding window, not fixed window. A fixed window lets a client send up to 2x their limit across a window boundary (e.g. 100 requests in the last second of one window, another 100 in the first second of the next). A sliding window evaluates "the last N seconds from right now," continuously, closing that gap.

**Redis data structure:** one sorted set per client — score is the request timestamp, member is a unique per-request ID.

**Key design:** `ratelimit:{scope}:{plan|identifier}:{client_id}`, e.g. `ratelimit:user:free:42`, `ratelimit:login:ip:203.0.113.5`. No PII embedded in keys.

**Atomicity:** the full sliding-window decision (remove expired entries, count, decide, record, set expiry) executes as a single Redis Lua script (`EVAL`), guaranteeing atomicity from Redis's perspective. This was a deliberate fix for a real race condition in an earlier implementation, where the same logic ran as four separate Redis round-trips — under concurrent load, two requests could both read the count before either wrote its entry, letting the limit be exceeded. Verified fixed via automated concurrency tests and a load benchmark showing exactly 100/100 allowed under a 100-request limit with 200 concurrent requests, zero overcounting.

**Client identity:** per-user limiting is keyed by `user_id`, resolved identically whether the request used a JWT or an API key — both share one bucket, since the limit applies to the user, not the credential mechanism. Login-attempt limiting is keyed by IP address, since no authenticated identity exists yet at that point — a separate, stricter limiter protecting against credential-stuffing.

**Redis failure strategy:** fails open. If Redis is unreachable or times out (2s socket timeout), the failure is logged with the request's correlation ID, and the request is allowed to proceed rather than blocking all traffic over a secondary feature's outage.

**429 response:**
```json
{"success": false, "error": {"code": 429, "message": "Rate limit exceeded: ...", "request_id": "..."}}
```
Includes a `Retry-After` header with an accurate seconds-until-reset value, calculated from the oldest entry still inside the window.

**Rate-limit headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on every non-enterprise response — omitted entirely for unlimited plans and during Redis fail-open, rather than showing misleading values.

**Concurrency considerations:** the atomic Lua script prevents race conditions *within a single Redis instance*. This does not provide distributed guarantees across multiple Redis instances/clusters — it assumes a single Redis deployment, which is the current architecture.

**Benchmark (measured, local dev environment):** 200 total requests, 20 concurrent clients, 100 req/hour limit, single-process Uvicorn dev server, local Postgres + Redis.

| Metric | Result |
|---|---|
| Requests/sec | 73.65 |
| Average latency | 263.83ms |
| p95 latency | 406.85ms |
| Allowed | 100 |
| Rejected (429) | 100 |
| Errors | 0 |

These figures reflect a local development environment, not a tuned production deployment. Re-run `benchmarks/rate_limit_bench.py` to reproduce.

---

## Security

**Authentication:** JWT for human/browser sessions (short-lived, signature + expiry + algorithm-pinned validation); API keys for machine-to-machine access (bcrypt-hashed at rest, raw value never re-exposed after creation). Routes intended only for human dashboard use (`/me`) accept JWT only; gateway/data routes accept either, since both resolve to the same `user_id`.

**Credential handling:** passwords and API keys are hashed with bcrypt; plaintext is never stored. Authentication headers are never written to logs — only the resolved `user_id`. Login failures return a generic message regardless of whether the email exists, preventing user enumeration.

**Rate limiting & brute-force protection:** general API rate limiting and login brute-force protection use separate Redis key namespaces and don't interfere with each other.

**CORS:** allowed origins are environment-configurable (`CORS_ALLOWED_ORIGINS`), not hardcoded — development and production can use different values without a code change.

**Input validation:** request bodies are validated via Pydantic (types, length constraints, numeric bounds). All database access goes through SQLAlchemy's ORM — no raw SQL string construction from user input exists anywhere in the codebase.

**Authorization boundaries:** authenticated identity is always derived from the validated JWT/API key, never from client-supplied request data. Extra fields in a request body (e.g. an attempted `user_id` override) are ignored by the schema and have no effect — verified by automated test.

**Secret management:** all secrets are environment-variable-driven, documented in `.env.example` with placeholder values only. `.env` is gitignored and confirmed never committed to this repository's history.

**Not implemented (explicitly out of scope):** refresh tokens, OAuth providers, RBAC, MFA, SSO.

---

## Reliability

**Configuration:** all config — database, Redis, JWT secrets, rate-limit thresholds, timeouts, CORS origins — is centralized in `app/core/config.py`, driven entirely by environment variables. Nothing is hardcoded in source.

**Request IDs:** every request is assigned a unique `X-Request-ID` (or the caller's own, if provided), returned in the response header and threaded through every log line and error response — enabling full request tracing without a distributed tracing system.

**Structured logging:** requests are logged as structured JSON to stdout — parseable by any standard log viewer without adopting an external observability platform.

**Health vs. readiness:** `GET /health` is liveness only — confirms the process is running, no dependency checks, stays fast. `GET /ready` checks PostgreSQL and Redis, returning `503` if either is unavailable, so traffic can be withheld without restarting a healthy process.

**Downstream timeout:** outbound calls to external services use an explicit, configurable timeout. Timeouts return `504`; connection failures return `502` — both logged with request ID correlation.

---

## Key Design Decisions

**Why Redis for rate limiting, but Postgres for logs?** Rate limiting needs extremely fast, short-lived, high-frequency counters — Redis is in-memory with native TTL and atomic operations. Logs are durable and need to be queried/aggregated later — exactly what Postgres is built for.

**Why sliding window over fixed window?** See Rate Limiting section above.

**Why soft delete for API keys?** Mirrors how real systems behave and preserves an audit trail rather than destroying history.

**Why a separate `X-API-Key` header instead of reusing `Authorization: Bearer`?** Keeps the two authentication mechanisms unambiguous — middleware can immediately tell which type of credential it's dealing with.

**Why simulated services instead of real separate deployments?** This project demonstrates the gateway *pattern* — routing, auth, rate limiting, logging applied centrally — without the operational overhead of running multiple real services for a portfolio project. Each simulated service is still backed by real, independent database models, structured so it could be split into a real deployment with minimal changes.

---

## Running Locally

### With Docker (recommended)

```bash
git clone <this-repo-url>
cd api_gateway
docker-compose up --build
```

App available at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`.

### Without Docker

Requires Python 3.12+, PostgreSQL, and Redis running locally.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# copy .env.example to .env and fill in real values

alembic upgrade head
uvicorn app.main:app --reload
```

## Running Tests

```bash
pytest -v
```

## Running the Rate Limiter Benchmark

```bash
python3 benchmarks/rate_limit_bench.py
```

---

## Project Status

Full MVP (12 modules) complete, plus four upgrade passes:
- **Reliability** — request IDs, structured logging, health/readiness split, Redis fail-open, downstream timeouts
- **Rate limiter engineering** — atomic Lua-based sliding window, standardized keys, concurrency-tested
- **Authentication & security hardening** — full audit, CORS fix, 14 new security tests
- **API design & database performance** — pagination, whitelisted sorting, Alembic migrations, indexing

All changes verified with an automated test suite (43 tests) and real, measured behavior — not assumed.