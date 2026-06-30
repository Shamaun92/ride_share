# RideShare API (Uber/Pathao clone) — Backend

Production-oriented FastAPI backend for a ride-sharing platform. This increment
ships the **foundation + complete authentication** (Phase 1 core).

## Architecture

Clean, layered separation so business logic stays framework-agnostic and testable:

```
HTTP (FastAPI routers)  ->  Services (business logic, tx boundary)
                        ->  Repositories (data access)
                        ->  Models (SQLAlchemy 2.0 async)
```

- **`app/core`** — config, async DB engine, Redis, security (bcrypt + JWT), exceptions, logging.
- **`app/models`** — `User` (single identity, role-discriminated), `DriverProfile` (1:1 with a driver user), `Vehicle`.
- **`app/schemas`** — Pydantic v2 request/response contracts.
- **`app/repositories`** — generic + entity repositories (no HTTP, no business rules).
- **`app/services`** — `AuthService` (register/login/refresh/logout) and `TokenService` (Redis-backed refresh-token revocation).
- **`app/api`** — dependencies (auth chain + RBAC) and versioned routers.

### Key design decisions
- **One identity table.** A driver is a `User(role=DRIVER)` plus a `DriverProfile`. Avoids duplicated credential logic; lets a person hold multiple roles later.
- **Refresh-token rotation + revocation via Redis.** Each refresh token carries a unique `jti` tracked in Redis with a TTL. Refresh rotates (old token invalidated); logout revokes. Instant revocation with no DB writes on the hot path.
- **Short-lived access tokens** (15 min) + long-lived refresh (7 days).
- **RBAC** via a `require_roles(...)` dependency factory.
- **Dialect-portable UUID PKs** (`sa.Uuid`) — native UUID on Postgres, works on SQLite for CI.

## Run with Docker (recommended)

```bash
cp .env.example .env          # set a strong SECRET_KEY (openssl rand -hex 32)
docker compose up --build
# API:        http://localhost:8000  (docs at /docs)
# Via Nginx:  http://localhost
```

Migrations run automatically on container start (`alembic upgrade head`).

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export SECRET_KEY="$(openssl rand -hex 32)"
# point POSTGRES_*/REDIS_* at local services, then:
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest -q     # runs on in-memory SQLite + fakeredis, no external services needed
```

## Auth API

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register rider |
| POST | `/api/v1/auth/register/driver` | Register driver (account + license + vehicle) |
| POST | `/api/v1/auth/login` | Login by email **or** phone |
| POST | `/api/v1/auth/refresh` | Rotate token pair |
| POST | `/api/v1/auth/logout` | Revoke a refresh token |
| GET  | `/api/v1/users/me` | Current user (any role) |
| GET  | `/api/v1/drivers/me` | Current driver profile + vehicles (RBAC: driver) |


## Phase 2 — Ride request system

Dispatch is modelled as explicit **ride offers**: when a rider requests a trip,
the system finds nearby ONLINE drivers (bounding-box + haversine) whose active
vehicle matches the requested type, and writes a `RideOffer` to each. The first
driver to accept **atomically claims** the ride via a conditional UPDATE
(`REQUESTED -> ACCEPTED`); everyone else gets a clean `409`. A central state
machine (`app/services/ride_state.py`) is the single source of truth for legal
transitions, so illegal moves are `409`s rather than corrupt data.

### Ride lifecycle

`REQUESTED -> ACCEPTED -> ARRIVED -> IN_PROGRESS -> COMPLETED`, with
`REQUESTED/ACCEPTED/ARRIVED -> CANCELLED` and `REQUESTED -> EXPIRED`.

### Rider endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/rides` | Request a ride; dispatches offers to nearby drivers |
| GET | `/api/v1/rides` | List my rides |
| GET | `/api/v1/rides/{ride_id}` | Get a ride (rider or assigned driver) |
| POST | `/api/v1/rides/{ride_id}/cancel` | Cancel (rider or assigned driver) |

### Driver endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| PATCH | `/api/v1/drivers/me/availability` | Go online / offline |
| PATCH | `/api/v1/drivers/me/location` | Update current location |
| GET | `/api/v1/drivers/me/offers` | List pending ride offers nearby |
| POST | `/api/v1/drivers/me/rides/{ride_id}/accept` | Accept (atomic claim) |
| POST | `/api/v1/drivers/me/rides/{ride_id}/reject` | Reject an offer |
| POST | `/api/v1/drivers/me/rides/{ride_id}/arrive` | Mark arrival at pickup |
| POST | `/api/v1/drivers/me/rides/{ride_id}/start` | Start the trip |
| POST | `/api/v1/drivers/me/rides/{ride_id}/complete` | Complete the trip |

Dispatch tuning lives in `Settings`: `RIDE_SEARCH_RADIUS_KM`,
`RIDE_MAX_OFFERS`, `RIDE_OFFER_TTL_SECONDS`. Fare is a placeholder
(`app/services/pricing.py`) to be replaced by the real engine in Phase 4.


## Phase 3 — Real-time tracking (WebSocket + Redis)

Live tracking runs over a single socket per ride, `WS /api/v1/ws/rides/{ride_id}`,
carrying both `location` and `ride_status` events to the rider and the assigned
driver. Auth is a JWT in the `token` query parameter (browsers can't set headers
on the WS handshake); membership is authorized once at connect, and a `snapshot`
is pushed immediately so reconnecting clients are instantly consistent.

### Pub/Sub backplane (horizontal scale)

Delivery goes through Redis Pub/Sub so it is correct across load-balanced
instances. Producers publish a JSON envelope to `rt:ride:{ride_id}`; every
instance runs a `WebSocketHub` that pattern-subscribes (`rt:ride:*`) and fans
each envelope out to the sockets it holds locally. A publisher never needs to
know which instance owns a recipient's socket.

### Live driver positions (Redis GEO)

Online drivers are kept in a Redis GEO set (`drivers:geo`). Dispatch now does a
`GEOSEARCH` for nearby candidates and refines against the DB for status and
vehicle type, falling back to the SQL bounding-box scan if the cache is cold or
Redis is unavailable. The DB keeps a denormalized last-known position for
durability and snapshots.

### Client → server messages

| Message | Who | Effect |
| ------- | --- | ------ |
| `{"type":"location","lat":..,"lng":..}` | assigned driver | GEO upsert + broadcast to the ride |
| `{"type":"ping"}` | either party | `{"type":"pong"}` heartbeat |

### Server → client events

`snapshot` (on connect) · `location` (driver moved) · `ride_status` (lifecycle
transition) · `pong` · `error`.

Driver location also updates via `PATCH /api/v1/drivers/me/location`, which
refreshes GEO and broadcasts to any active ride — the WS stream is the primary
path, REST is the fallback. nginx proxies `/api/v1/ws/` with the connection
upgrade headers already configured.


## Phase 4 — Fare engine, wallet, payments, ratings

All money is integer **poisha** (1 BDT = 100 poisha) to keep ledger arithmetic
exact; `ride.final_fare` is only a display projection of the canonical payment.

### Fare engine (`app/services/pricing.py`)

Fare = booking fee + base + distance + time, scaled by a vehicle multiplier and
a surge multiplier (default 1.0 — the Phase 6 seam), floored at a minimum.
`estimate` runs at request time (duration inferred from an assumed city speed);
`finalize` runs at completion using the **real elapsed trip duration**.

### Double-entry ledger

Every financial event is a `LedgerTransaction` whose `LedgerEntry` postings sum
to exactly zero — enforced in `LedgerService.post` and asserted in tests. Wallet
balances are a projection of the ledger. Accounts: rider wallet, driver wallet,
platform revenue, cash clearing.

Settlement at completion splits the fare: the platform commission goes to
`PLATFORM_REVENUE`, the rest to the driver. For **wallet** rides the rider is
debited and the driver credited; for **cash** rides the fare is exchanged
off-ledger and only the commission the driver owes is posted. A late
cancellation (rider cancels after a driver committed) charges a fee that
compensates the driver, and `PaymentService.refund_payment` reverses any
transaction by posting its mirror image.

### Ratings

Riders rate drivers and vice versa, once per completed ride; rating a driver
updates `DriverProfile.rating_avg`/`rating_count` incrementally (O(1) reads).

### New endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/wallet` | Balance + recent ledger activity |
| POST | `/api/v1/wallet/topup` | Add funds |
| GET | `/api/v1/rides/{ride_id}/receipt` | Fare breakdown, payment, my rating |
| POST | `/api/v1/rides/{ride_id}/rate` | Rate the other party |

`POST /rides` now accepts `payment_method` (`cash` | `wallet`). Economics are
tunable via settings: `FARE_*_POISHA`, `PLATFORM_COMMISSION_BPS`,
`CANCELLATION_FEE_POISHA`, `FARE_AVG_SPEED_KMH`.


## Phase 5 — Scheduled rides, promo codes, notifications

**Scheduled rides.** A request with a future `scheduled_for` is stored as
`SCHEDULED` rather than dispatched. A worker (`python -m app.workers.scheduler`,
or `POST /admin/scheduler/run`) calls `SchedulerService.dispatch_due`, which
finds due rides, recomputes surge, transitions them to `REQUESTED`, and offers
them out through the normal dispatch flow.

**Promo codes.** `PERCENT` (basis points) or `FLAT` (poisha) discounts with
validity windows, global and per-user usage limits, minimum fare, and an
optional cap. `PromoService.quote` validates without persisting (preview via
`POST /promos/quote`); the discount is applied and redeemed at settlement. The
discount is **funded by the platform** through a `PROMO_EXPENSE` ledger posting,
so the driver is paid on the gross fare while the rider pays less — and the
double-entry transaction still nets to zero.

**Notifications.** Ride-lifecycle events (`accepted`, `arrived`, `started`,
`completed`, `cancelled`, `scheduled`, `dispatched`) are persisted as
`Notification` rows and published live to the rider/driver's personal channel
`rt:user:{id}`. Queryable via `GET /notifications` with unread counts and
mark-read; streamed in real time over `WS /ws/notifications`.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/api/v1/promos/quote` | Preview a promo discount |
| GET | `/api/v1/notifications` | List notifications + unread count |
| POST | `/api/v1/notifications/{id}/read` | Mark one read |
| POST | `/api/v1/notifications/read-all` | Mark all read |
| WS | `/api/v1/ws/notifications` | Live notification stream |

`POST /rides` now also accepts `scheduled_for`, `promo_code`, and `shared`.

## Phase 6 — Surge pricing, ride pooling, admin

**Surge.** `SurgeService.compute_bps` reads live supply (nearby drivers from the
Redis GEO index) and demand (open `REQUESTED` rides in the area) and raises the
multiplier when demand outstrips supply, capped at `SURGE_MAX_BPS`. The fare
engine already takes a surge multiplier; the computed value is stored on the
ride at request time and reused at settlement. Preview via `GET /pricing/surge`.

**Pooling.** A `shared` ride joins an `OPEN` `RidePool` whose coarse pickup
bucket matches (or seeds a new one) and receives a `POOL_DISCOUNT_BPS` discount
applied to the gross fare at settlement. Full multi-stop trip sequencing is the
next iteration; this layer delivers matching, grouping, and discounted shared
fares.

**Admin.** Role-gated (`ADMIN`) operations dashboard: platform metrics (rides by
status, platform revenue and promo spend straight from the ledger, active
drivers, user counts), ride/driver listings, driver verification, promo
creation, a refund endpoint that reverses a payment's ledger transaction, and a
manual scheduler trigger. Admins are seeded via secret-gated `POST
/admin/bootstrap`.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/api/v1/pricing/surge` | Current surge at a location |
| POST | `/api/v1/admin/bootstrap` | Promote a user to admin (secret) |
| GET | `/api/v1/admin/metrics` | Platform metrics |
| GET | `/api/v1/admin/rides` · `/admin/drivers` | Listings |
| PATCH | `/api/v1/admin/drivers/{id}/verify` | Set verification status |
| POST | `/api/v1/admin/promos` | Create a promo code |
| POST | `/api/v1/admin/payments/{id}/refund` | Refund (reverses ledger) |
| POST | `/api/v1/admin/scheduler/run` | Dispatch due scheduled rides |

This completes the six-phase backend: auth, ride lifecycle, real-time tracking,
payments/ledger, scheduling/promos/notifications, and surge/pooling/admin.


## Phase 7 — Production hardening

Cross-cutting safety added without new tables (Redis- and log-backed).

**Idempotency.** `IdempotencyMiddleware` replay-protects `POST`/`PATCH` requests
that carry an `Idempotency-Key` header: the first 2xx response for a
(caller, method, path, key) tuple is cached in Redis and replayed verbatim on
retry (flagged with `X-Idempotent-Replay: true`), so a client retry can't create
a second charge or duplicate ride. No-ops cleanly when Redis is unavailable.

**Rate limiting.** Fixed-window Redis counters via dependencies: per-user limits
on money-touching mutations (`POST /rides`, `POST /wallet/topup`) and per-IP
limits on auth endpoints (`register`, `login`). Limits are read from settings at
call time and fail open if the limiter errors. Exceeding a limit returns `429`.

**Request context + security headers.** `RequestContextMiddleware` attaches an
`X-Request-ID` correlation id to every request/response (echoing an inbound one
if present) and sets `X-Content-Type-Options`, `X-Frame-Options`,
`Referrer-Policy`, and `X-XSS-Protection`.

**Audit trail.** A dedicated `audit` logger emits structured JSON lines for
security- and money-relevant events — `auth.login`, `payment.settled`,
`payment.refunded`, `admin.driver_verified`, `admin.promo_created`,
`admin.bootstrapped` — ready to ship to a SIEM / immutable store.

New settings: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_DEFAULT_PER_MIN`,
`RATE_LIMIT_AUTH_PER_MIN`, `IDEMPOTENCY_TTL_SECONDS`, `SECURITY_HEADERS_ENABLED`.
