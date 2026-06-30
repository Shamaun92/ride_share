# Shohojatri — frontend

A real-time ride-hailing console for the Shohojatri backend (FastAPI · PostgreSQL ·
Redis · WebSockets). Built with Next.js 14 (App Router), TypeScript, and Tailwind.

## Design

**"Dispatch" — a live operations console.** Warm paper app surface with a dark
live-map console as the signature element. Transit **teal** is the primary,
**jade** marks "go / live", **amber** marks surge. Type pairs **Space Grotesk**
(display) with **Inter** (body) and renders all telemetry — fares, coordinates,
ETAs — in **JetBrains Mono**, like a console readout. The one bold move is the
live dispatch console: a pulsing driver ping over a projected map, a mono
telemetry strip, and a status timeline that fills as the trip advances.

## What's here

- **Landing** (`/`) — product hero with a live console preview.
- **Auth** (`/login`, `/register`) — rider sign-in/up; tokens persisted, with a
  transparent refresh-on-401 in the API client.
- **Ride** (`/ride`) — the centerpiece. Pick a route, see live surge + a fare
  estimate (mirrors the backend pricing engine), choose vehicle / payment /
  pooling / promo, then request. Once active, a live console tracks the trip over
  a WebSocket (`/ws/rides/{id}`): status timeline, driver card, animated driver
  position, and a receipt + star rating on completion.
- **Wallet** (`/wallet`) — balance, one-tap top-ups, and the ledger activity feed.
- **History** (`/history`) — past rides with fares and status.
- **Console** (`/admin`) — platform metrics from the ledger (admins only).

## Architecture

```
src/
  lib/        types (mirror backend schemas), api client (typed, auto-refresh),
              auth context, useRideSocket (WebSocket), fare projection, formatters
  components/ ui primitives, Logo, Nav, DispatchMap (SVG), Telemetry, RideTimeline
  app/        landing, login, register, and the authed (app) group with route guard
```

The map is a self-contained SVG that projects lat/lng to a viewport — no tile
dependency, so it always renders. Swap `components/Map.tsx` for `react-leaflet` +
OpenStreetMap tiles to put it on real streets; the projection seam is isolated.

## Run it

```bash
cp .env.local.example .env.local   # point at your backend
npm install
npm run dev                        # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_WS_BASE` to your running backend
(`docker-compose up` in `../backend` exposes `http://localhost:8000`).

```bash
npm run build       # production build
npm run typecheck   # tsc --noEmit
```

> Fonts load at runtime via a stylesheet `<link>` (so builds don't need network
> access to Google Fonts). Switch to `next/font/google` if you prefer self-hosting.
