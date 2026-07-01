# Shohojatri

A ride-hailing web app modeled on Uber/Pathao — riders request rides, drivers
accept them, and both sides see the trip progress live over a WebSocket. Built
as a full-stack portfolio project.

**Stack:** FastAPI · PostgreSQL · Redis · Next.js 14 · TypeScript · Tailwind · Docker

---

## What actually works

Every item below is exercised by tests or wired end-to-end in the UI.

**Riders**
- Register, log in, refresh tokens automatically on 401.
- Request a ride: pick pickup + drop-off, choose vehicle (car / bike / CNG),
  choose payment (wallet / cash), optionally opt into pooling or apply a promo.
- See a live fare estimate that mirrors the backend pricing engine, including
  surge multiplier at the pickup location.
- Watch the trip on a live console: status timeline, driver card, animated
  driver ping over an SVG map, receipt on completion, star-rate the driver.
- Wallet with top-ups and a ledger-backed activity feed.
- Ride history with fares and statuses.

**Drivers**
- Register with license + vehicle details, go online, stream location.
- Receive nearby ride offers, accept/reject, then progress the trip:
  `accepted → arrived → in_progress → completed`.

**Admin**
- Bootstrap the first admin via a secret-gated endpoint.
- Console with platform metrics (rides, revenue, active drivers) from the ledger.

**Behind the scenes**
- **JWT auth** — short-lived access token (15 min) + long-lived refresh (7 days).
  Refresh tokens rotate on every use; each `jti` is tracked in Redis so logout
  and rotation cause instant revocation without a DB write.
- **Real-time updates** — Redis pub/sub fans out ride events to any WebSocket
  subscribed to that ride. Status changes, driver location, and pool joins all
  flow through the same channel.
- **Money in poisha** — all currency is stored as integer poisha (1 BDT = 100
  poisha) to avoid float rounding. Fares compute as: booking fee + base +
  distance + time, scaled by a vehicle multiplier and a surge multiplier,
  floored at a minimum.
- **Double-entry ledger** — every payment posts balanced debits and credits
  across logical accounts (rider wallet, driver wallet, platform revenue, cash
  clearing, promo expense).
- **Hardening middleware** — request-id logging, security headers, per-user +
  per-IP rate limits, and an `Idempotency-Key` replay guard on mutations.

---

## Tech stack — and why

| Layer | Choice | Why |
| --- | --- | --- |
| API framework | FastAPI | Async, typed via Pydantic v2, free OpenAPI docs at `/docs`. |
| ORM | SQLAlchemy 2.0 async | Real async DB access; type-hinted models. |
| Database | PostgreSQL 16 | Transactions for money, native UUID PKs. |
| Cache / realtime | Redis 7 | JWT revocation, pub/sub for WebSockets, rate-limit counters. |
| Migrations | Alembic | Version-controlled schema. |
| Frontend | Next.js 14 (App Router) | File-based routing, RSC-ready, TypeScript-native. |
| Styling | Tailwind CSS | Design tokens as classes, no runtime CSS. |
| Container | Docker Compose | One command spins up db + redis + api + nginx. |

---

## Architecture at a glance

```
┌─────────────────┐   HTTP + WebSocket   ┌────────────────────┐
│  Next.js 14     │  ───────────────▶    │  FastAPI (uvicorn) │
│  (React/TS)     │  ◀───────────────    │  behind nginx      │
└─────────────────┘                      └──────────┬─────────┘
                                                    │
                                       ┌────────────┼─────────────┐
                                       ▼            ▼             ▼
                                 ┌─────────┐   ┌────────┐   ┌───────────┐
                                 │Postgres │   │ Redis  │   │  Alembic  │
                                 │ (data)  │   │(pubsub,│   │(migrations│
                                 │         │   │ tokens,│   │ on boot)  │
                                 │         │   │ rate)  │   │           │
                                 └─────────┘   └────────┘   └───────────┘
```

**Backend is layered so business logic stays framework-agnostic:**

```
HTTP (routers)  →  Services (business logic, tx boundary)
                →  Repositories (data access)
                →  Models (SQLAlchemy)
```

- `backend/app/api/v1/endpoints/` — HTTP + WebSocket routes.
- `backend/app/services/` — one service per concern: auth, rides, pricing,
  surge, pooling, wallet, ledger, ratings, notifications, scheduler, admin.
- `backend/app/models/` — SQLAlchemy models + shared enums.
- `backend/app/ws/` — connection manager and Redis-backed event fan-out.
- `backend/app/core/` — config, DB, Redis, security, middleware, exceptions.

**Frontend layout:**
- `frontend/src/app/` — pages (App Router). Authed pages live under `(app)/`.
- `frontend/src/lib/` — typed API client (auto-refresh on 401), auth context,
  WebSocket hook, fare projection, formatters.
- `frontend/src/components/` — Map, Nav, RideTimeline, Telemetry, UI primitives.

---

## Ride lifecycle (state machine)

```
requested ──▶ accepted ──▶ arrived ──▶ in_progress ──▶ completed
    │             │           │             │
    ▼             ▼           ▼             ▼
 expired      cancelled   cancelled     cancelled
(no driver    (rider/     (rider/       (rider/
 in time)     driver)     driver)       driver)

scheduled ──(due)──▶ requested   (scheduler_service dispatches)
```

The service layer enforces the transitions. Illegal transitions raise a domain
error that maps to a 409 in HTTP.

---

## Run it locally

You need **Docker Desktop** and **Node.js LTS**.

### 1) Backend

```bash
cd backend
cp .env.example .env    # already good defaults for local
docker compose up --build
```

First run pulls Postgres + Redis (~500 MB) and builds the API image (2–5 min).
Ready when you see `Application startup complete`.

- API: <http://localhost:8000/docs> (Swagger)
- Via nginx: <http://localhost>

### 2) Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000>. Register → request a ride → watch the live console.

### 3) Become an admin (optional)

```bash
curl -X POST http://localhost:8000/api/v1/admin/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","secret":"admin-secret-local"}'
```

Sign out, sign back in, the **Console** tab appears in the nav.

---

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

**50 tests, all passing** — covers auth, ride lifecycle, payments/ledger,
scheduling + promos, surge + pooling + admin, WebSockets end-to-end, rate
limiting + idempotency + security headers. Tests run on in-memory SQLite +
`fakeredis`, so no Docker needed for the suite.

---

## Repository layout

```
shohojatri/
├── backend/
│   ├── app/
│   │   ├── api/          HTTP + WebSocket endpoints (v1)
│   │   ├── core/         config, DB, Redis, security, middleware
│   │   ├── models/       SQLAlchemy models + enums
│   │   ├── repositories/ data access
│   │   ├── schemas/      Pydantic request/response contracts
│   │   ├── services/     business logic (one file per concern)
│   │   ├── workers/      background workers
│   │   └── ws/           WebSocket hub (Redis pub/sub)
│   ├── alembic/          database migrations
│   ├── tests/            50 pytest tests
│   ├── docker-compose.yml
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/          pages (Next.js App Router)
    │   ├── components/   UI + Map + Timeline + Telemetry
    │   └── lib/          API client, auth, WebSocket, types
    └── .env.local.example
```

---

## Known limitations (be honest with reviewers)

These are deliberate portfolio-scope choices — not oversights:

- **Map is an SVG projection**, not real streets. `Map.tsx` isolates the
  projection so swapping in `react-leaflet` + OpenStreetMap tiles is a one-file
  change.
- **Payments are simulated.** The wallet + ledger are real (double-entry,
  balanced), but no external payment gateway is wired in.
- **Dispatch is proximity-based**, not ETA/traffic-aware — nearest online
  driver within a configurable radius.
- **Notifications are in-app only** (WebSocket + REST). No SMS/email/push.
- **No production hosting.** Runs locally via Docker Compose; no k8s manifests
  or CI/CD.

---

## Common questions

**Why one `User` table for riders and drivers?**
Single identity, one credential path, RBAC via a `role` column. A driver is
just a `User(role=driver)` with a 1:1 `DriverProfile`. Lets a person hold
multiple roles later without duplicating auth.

**Why store money as integer poisha?**
Float arithmetic loses precision on money. Poisha (1/100 BDT) keeps all fare
math in integers; formatting happens at the edge.

**Why Redis for both JWT and WebSockets?**
Two problems, one primitive. Refresh-token `jti`s live in Redis with a TTL —
logout deletes the key, rotation replaces it, so revocation is O(1) with no DB
write. The WebSocket hub subscribes to a per-ride Redis channel, so any API
worker can publish a ride event and every connected client sees it.

**How do you prevent double-billing on retries?**
Mutations accept an `Idempotency-Key` header; the middleware caches the
response for the configured TTL and replays it on retry.

**What would you change for production?**
Real map tiles, payment gateway, push notifications, dispatch that considers
ETA/traffic, horizontal scaling for the WebSocket hub (Redis pub/sub already
supports this), managed Postgres + Redis, structured audit logs shipped to a
SIEM, and rate-limit counters keyed on authenticated user + route bucket.
