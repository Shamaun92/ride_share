# Shohojatri — Backend

FastAPI backend for a ride-hailing platform: authentication, ride dispatch and
lifecycle, real-time tracking over WebSockets, payments on a double-entry
ledger, scheduled rides, promo codes, surge pricing, pooling, an admin console,
and production-hardening middleware.

## Architecture

Layered so the business logic stays independent of the web framework and stays
testable:

```
HTTP (FastAPI routers)  ->  Services (business logic, transaction boundary)
                        ->  Repositories (data access)
                        ->  Models (SQLAlchemy 2.0 async)
```

- **`app/core`** — config, async DB engine, Redis, security (bcrypt + JWT),
  middleware, exceptions, logging.
- **`app/models`** — SQLAlchemy models and shared enums.
- **`app/schemas`** — Pydantic v2 request/response contracts.
- **`app/repositories`** — data access, no HTTP and no business rules.
- **`app/services`** — one service per concern (auth, rides, pricing, surge,
  pooling, wallet, ledger, ratings, promos, notifications, scheduler, admin).
- **`app/ws`** — WebSocket hub and the Redis pub/sub event fan-out.
- **`app/api`** — dependencies (auth chain + RBAC) and the versioned routers.

### Key design decisions

- **One identity table.** A driver is a `User(role=DRIVER)` with a 1:1
  `DriverProfile`, so there's a single credential path and a person could hold
  more than one role later.
- **Refresh-token rotation and revocation via Redis.** Each refresh token
  carries a unique `jti` tracked in Redis with a TTL. Refreshing rotates it (the
  old one is invalidated) and logout revokes it, so revocation is instant with
  no write on the hot path.
- **Short access tokens** (15 min) and longer refresh tokens (7 days).
- **RBAC** through a `require_roles(...)` dependency factory.
- **Money as integer poisha** (1 BDT = 100 poisha) so ledger arithmetic stays
  exact.
- **Dialect-portable UUID keys** (`sa.Uuid`): native UUID on Postgres, and they
  also work on SQLite, which the test suite uses.

## Running

### With Docker (recommended)

```bash
cp .env.example .env          # set a strong SECRET_KEY (openssl rand -hex 32)
docker compose up --build
# API:       http://localhost:8000  (docs at /docs)
# Via nginx: http://localhost
```

Migrations run automatically on container start (`alembic upgrade head`).

### Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export SECRET_KEY="$(openssl rand -hex 32)"
# point POSTGRES_* / REDIS_* at local services, then:
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest -q     # in-memory SQLite + fakeredis, no external services needed
```

## API reference

### Auth & users

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a rider |
| POST | `/api/v1/auth/register/driver` | Register a driver (account + license + vehicle) |
| POST | `/api/v1/auth/login` | Log in by email **or** phone |
| POST | `/api/v1/auth/refresh` | Rotate the token pair |
| POST | `/api/v1/auth/logout` | Revoke a refresh token |
| GET  | `/api/v1/users/me` | Current user (any role) |
| GET  | `/api/v1/drivers/me` | Current driver profile + vehicles (driver only) |

### Rides (rider)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/rides` | Request a ride; dispatches offers to nearby drivers |
| GET | `/api/v1/rides` | List my rides |
| GET | `/api/v1/rides/{ride_id}` | Get a ride (rider or assigned driver) |
| POST | `/api/v1/rides/{ride_id}/cancel` | Cancel (rider or assigned driver) |
| GET | `/api/v1/rides/{ride_id}/receipt` | Fare breakdown, payment, my rating |
| POST | `/api/v1/rides/{ride_id}/rate` | Rate the other party |

`POST /rides` accepts `payment_method` (`cash` \| `wallet`), and optionally
`scheduled_for`, `promo_code`, and `shared`.

### Driver operations

| Method | Path | Purpose |
|---|---|---|
| PATCH | `/api/v1/drivers/me/availability` | Go online / offline |
| PATCH | `/api/v1/drivers/me/location` | Update current location |
| GET | `/api/v1/drivers/me/offers` | List pending ride offers nearby |
| POST | `/api/v1/drivers/me/rides/{ride_id}/accept` | Accept (atomic claim) |
| POST | `/api/v1/drivers/me/rides/{ride_id}/reject` | Reject an offer |
| POST | `/api/v1/drivers/me/rides/{ride_id}/arrive` | Mark arrival at pickup |
| POST | `/api/v1/drivers/me/rides/{ride_id}/start` | Start the trip |
| POST | `/api/v1/drivers/me/rides/{ride_id}/complete` | Complete the trip |

### Wallet, pricing, promos & notifications

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/wallet` | Balance + recent ledger activity |
| POST | `/api/v1/wallet/topup` | Add funds |
| GET | `/api/v1/pricing/surge` | Current surge multiplier at a location |
| POST | `/api/v1/promos/quote` | Preview a promo discount |
| GET | `/api/v1/notifications` | List notifications + unread count |
| POST | `/api/v1/notifications/{id}/read` | Mark one read |
| POST | `/api/v1/notifications/read-all` | Mark all read |
| WS | `/api/v1/ws/rides/{ride_id}` | Live ride tracking |
| WS | `/api/v1/ws/notifications` | Live notification stream |

### Admin (role-gated)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/admin/bootstrap` | Promote a user to admin (secret-gated) |
| GET | `/api/v1/admin/metrics` | Platform metrics |
| GET | `/api/v1/admin/rides` · `/admin/drivers` | Listings |
| PATCH | `/api/v1/admin/drivers/{id}/verify` | Set verification status |
| POST | `/api/v1/admin/promos` | Create a promo code |
| POST | `/api/v1/admin/payments/{id}/refund` | Refund (reverses the ledger transaction) |
| POST | `/api/v1/admin/scheduler/run` | Dispatch due scheduled rides |

## How it works

### Dispatch

Dispatch is modelled as explicit **ride offers**. When a rider requests a trip,
the system finds nearby ONLINE drivers whose active vehicle matches the
requested type and writes a `RideOffer` to each. The first driver to accept
atomically claims the ride with a conditional UPDATE (`REQUESTED → ACCEPTED`);
everyone else gets a clean `409`. A state machine in
`app/services/ride_state.py` is the single source of truth for legal
transitions, so an illegal move is a `409` rather than corrupt data. The
lifecycle is `REQUESTED → ACCEPTED → ARRIVED → IN_PROGRESS → COMPLETED`, with
`REQUESTED/ACCEPTED/ARRIVED → CANCELLED` and `REQUESTED → EXPIRED`. Tuning lives
in settings: `RIDE_SEARCH_RADIUS_KM`, `RIDE_MAX_OFFERS`, `RIDE_OFFER_TTL_SECONDS`.

### Real-time tracking

Each ride has one socket, `WS /api/v1/ws/rides/{ride_id}`, carrying `location`
and `ride_status` events to the rider and the assigned driver. Auth is a JWT in
the `token` query parameter (browsers can't set headers on the WS handshake);
membership is authorized once at connect, and a `snapshot` is pushed
immediately so a reconnecting client is instantly consistent.

Delivery runs through Redis pub/sub so it stays correct across load-balanced
instances. Producers publish a JSON envelope to `rt:ride:{ride_id}`; every
instance runs a `WebSocketHub` that pattern-subscribes to `rt:ride:*` and fans
each envelope out to the sockets it holds locally, so a publisher never needs to
know which instance owns a recipient. Online drivers live in a Redis GEO set;
dispatch does a `GEOSEARCH` for candidates and refines against the DB, falling
back to a SQL bounding-box scan if the cache is cold or Redis is down. Driver
location also updates over `PATCH /api/v1/drivers/me/location` as a REST
fallback to the WS stream.

### Fares & the ledger

A fare is booking fee + base + distance + time, scaled by a vehicle multiplier
and a surge multiplier and floored at a minimum. `pricing.estimate` runs at
request time (duration inferred from an assumed city speed) and
`pricing.finalize` runs at completion using the real elapsed trip duration.

Every financial event is a `LedgerTransaction` whose entries sum to exactly zero
(enforced in `LedgerService.post` and asserted in tests); wallet balances are a
projection of the ledger. At completion the fare splits between the driver and
`PLATFORM_REVENUE`. Wallet rides debit the rider and credit the driver; cash
rides are settled off-ledger except for the commission the driver owes. A late
cancellation charges a fee that compensates the driver, and a refund posts the
mirror image of the original transaction. Economics are tunable via
`FARE_*_POISHA`, `PLATFORM_COMMISSION_BPS`, `CANCELLATION_FEE_POISHA`, and
`FARE_AVG_SPEED_KMH`.

### Scheduled rides, promos & notifications

A request with a future `scheduled_for` is stored as `SCHEDULED` instead of
being dispatched. A worker (`python -m app.workers.scheduler`, or
`POST /admin/scheduler/run`) finds due rides, recomputes surge, moves them to
`REQUESTED`, and offers them out through the normal flow.

Promo codes are `PERCENT` (basis points) or `FLAT` (poisha) with validity
windows, global and per-user limits, a minimum fare, and an optional cap.
`PromoService.quote` validates without persisting; the discount is redeemed at
settlement and funded by the platform through a `PROMO_EXPENSE` posting, so the
driver is still paid on the gross fare and the transaction nets to zero.

Ride-lifecycle events are stored as `Notification` rows and published live to
each user's channel `rt:user:{id}`, queryable over REST and streamed over
`WS /ws/notifications`.

### Surge & pooling

`SurgeService.compute_bps` reads live supply (nearby drivers in the GEO index)
and demand (open `REQUESTED` rides nearby) and raises the multiplier when demand
outstrips supply, capped at `SURGE_MAX_BPS`. The value is stored on the ride at
request time and reused at settlement.

A `shared` ride joins an `OPEN` `RidePool` whose coarse pickup bucket matches
(or seeds a new one) and gets a `POOL_DISCOUNT_BPS` discount on the gross fare.
Full multi-stop sequencing would be the next step; this layer handles matching,
grouping, and discounted shared fares.

### Hardening

Cross-cutting safety, all Redis- or log-backed (no extra tables):

- **Idempotency.** `IdempotencyMiddleware` caches the first 2xx response for a
  `POST`/`PATCH` carrying an `Idempotency-Key` and replays it verbatim on retry
  (flagged with `X-Idempotent-Replay: true`), so a client retry can't create a
  second charge. It no-ops when Redis is unavailable.
- **Rate limiting.** Fixed-window Redis counters: per-user limits on
  money-touching mutations and per-IP limits on the auth endpoints. Exceeding a
  limit returns `429`; the limiter fails open on error.
- **Request context and security headers.** `RequestContextMiddleware` attaches
  an `X-Request-ID` to every request/response and sets `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, and `X-XSS-Protection`.
- **Audit trail.** A dedicated `audit` logger emits structured JSON for
  security- and money-relevant events (`auth.login`, `payment.settled`,
  `payment.refunded`, `admin.*`), ready to ship to a SIEM.

Settings: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_DEFAULT_PER_MIN`,
`RATE_LIMIT_AUTH_PER_MIN`, `IDEMPOTENCY_TTL_SECONDS`, `SECURITY_HEADERS_ENABLED`.
