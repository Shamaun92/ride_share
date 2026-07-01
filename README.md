# Shohojatri

A ride-hailing web app (think Uber or Pathao) where riders request rides,
drivers accept them, and both sides follow the trip live over a WebSocket. I
built it as a full-stack portfolio project.

**Stack:** FastAPI, PostgreSQL, Redis, Next.js 14, TypeScript, Tailwind, Docker.

---

## Features

**Riders**
- Register and log in. The frontend refreshes the access token automatically
  when it expires, so sessions don't drop mid-ride.
- Request a ride: choose pickup and drop-off, pick a vehicle (car, bike, or
  CNG) and payment method (wallet or cash), and optionally pool the ride or add
  a promo code.
- Get a live fare estimate that matches the backend pricing engine, including
  the current surge multiplier at the pickup point.
- Track the trip on a live map: status timeline, driver details, the driver's
  position updating in real time, and a receipt plus star rating at the end.
- A wallet with top-ups and a running activity feed.
- Ride history with fares and statuses.

**Drivers**
- Register with license and vehicle details, go online, and stream location.
- Get offers for nearby rides, accept or reject them, and move the trip through
  `accepted → arrived → in_progress → completed`.

**Admin**
- Promote the first admin through a secret-gated endpoint.
- A metrics console (rides, revenue, active drivers) built from the ledger.

**Under the hood**
- JWT auth with a short access token (15 min) and a longer refresh token (7
  days). Refresh tokens rotate on each use and their IDs are tracked in Redis,
  so logging out or rotating revokes them immediately without a database write.
- Redis pub/sub pushes ride events (status changes, driver location, pool
  joins) to every WebSocket watching that ride.
- Money is stored as integer poisha (1 BDT = 100 poisha) to avoid
  floating-point rounding. A fare is booking fee + base + distance + time,
  scaled by vehicle and surge multipliers and floored at a minimum.
- Payments post to a double-entry ledger, so every charge has balanced debits
  and credits across the rider wallet, driver wallet, platform revenue, cash
  clearing, and promo accounts.
- Request middleware adds request-id logging, security headers, per-user and
  per-IP rate limits, and an `Idempotency-Key` guard so a retried request never
  charges twice.

---

## Tech stack

| Layer | Choice | Notes |
| --- | --- | --- |
| API framework | FastAPI | Async, typed with Pydantic v2, and generates OpenAPI docs at `/docs`. |
| ORM | SQLAlchemy 2.0 (async) | Async database access with typed models. |
| Database | PostgreSQL 16 | Transactions for the money paths, native UUID keys. |
| Cache / realtime | Redis 7 | Token revocation, pub/sub for WebSockets, rate-limit counters. |
| Migrations | Alembic | Version-controlled schema. |
| Frontend | Next.js 14 (App Router) | File-based routing and TypeScript throughout. |
| Styling | Tailwind CSS | Utility classes, no runtime CSS. |
| Container | Docker Compose | One command brings up db, redis, api, and nginx. |

---

## Architecture

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

The backend is layered so the business logic stays independent of the web
framework:

```
HTTP (routers)  →  Services (business logic, transaction boundary)
                →  Repositories (data access)
                →  Models (SQLAlchemy)
```

- `backend/app/api/v1/endpoints/` — HTTP and WebSocket routes.
- `backend/app/services/` — one service per concern: auth, rides, pricing,
  surge, pooling, wallet, ledger, ratings, notifications, scheduler, admin.
- `backend/app/models/` — SQLAlchemy models and shared enums.
- `backend/app/ws/` — connection manager and Redis-backed event fan-out.
- `backend/app/core/` — config, DB, Redis, security, middleware, exceptions.

On the frontend:

- `frontend/src/app/` — pages (App Router); authed pages live under `(app)/`.
- `frontend/src/lib/` — the API client (with auto token refresh), auth context,
  WebSocket hook, fare projection, and formatters.
- `frontend/src/components/` — Map, Nav, RideTimeline, Telemetry, and UI
  primitives.

---

## Ride lifecycle

```
requested ──▶ accepted ──▶ arrived ──▶ in_progress ──▶ completed
    │             │           │             │
    ▼             ▼           ▼             ▼
 expired      cancelled   cancelled     cancelled
(no driver    (rider/     (rider/       (rider/
 in time)     driver)     driver)       driver)

scheduled ──(due)──▶ requested   (dispatched by the scheduler)
```

The service layer enforces these transitions. An illegal transition raises a
domain error that the API turns into a 409.

---

## Running locally

You'll need **Docker Desktop** and **Node.js LTS**.

### 1) Backend

```bash
cd backend
cp .env.example .env    # defaults are fine for local
docker compose up --build
```

The first run pulls Postgres and Redis (~500 MB) and builds the API image, so
give it a few minutes. It's ready when you see `Application startup complete`.

- API and Swagger docs: <http://localhost:8000/docs>
- Through nginx: <http://localhost>

### 2) Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000>, register, request a ride, and watch it track live.

### 3) Become an admin (optional)

```bash
curl -X POST http://localhost:8000/api/v1/admin/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","secret":"admin-secret-local"}'
```

Sign out and back in, and the **Console** tab shows up in the nav.

---

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

The suite (50 tests) covers auth, the ride lifecycle, payments and the ledger,
scheduling and promos, surge, pooling, admin metrics, the WebSocket endpoint
end-to-end, and the rate-limiting / idempotency / security-header middleware.
It runs against in-memory SQLite and `fakeredis`, so you don't need Docker to
run it.

---

## Project layout

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
│   ├── tests/            pytest suite
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

## Limitations

A few things are intentionally out of scope for a portfolio build:

- The map is a hand-drawn SVG, not real street tiles. The projection is
  isolated in `Map.tsx`, so swapping in react-leaflet with OpenStreetMap tiles
  would be a contained change.
- Payments are simulated. The wallet and ledger are real and balanced, but
  there's no external payment gateway.
- Dispatch picks the nearest available driver within a radius; it doesn't
  account for ETA or traffic.
- Notifications are in-app only (WebSocket and REST) — no SMS, email, or push.
- It runs locally with Docker Compose. There's no cloud deployment, CI, or
  Kubernetes setup.
