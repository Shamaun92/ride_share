# Shohojatri — Frontend

Next.js 14 (App Router), TypeScript, and Tailwind. The rider-facing web app for
the Shohojatri backend, with a map-forward ride flow and live trip tracking over
WebSockets.

## Design

A modern, map-forward ride-hailing UI: cool neutral surfaces with a single teal
accent (jade for "live/go", amber for surge), rounded cards and bottom sheets,
and a light, street-style map drawn as an SVG. Headings use Space Grotesk, body
text uses Inter, and numbers (fares, coordinates, ETAs) use JetBrains Mono. The
ride screen is the centrepiece: a full-height map with a bottom sheet for
choosing route, vehicle, and payment, and a live console that follows the driver
as the trip progresses.

## Pages

- **Landing** (`/`) — a hero with a phone preview of the live map.
- **Auth** (`/login`, `/register`) — rider sign-in and sign-up. Tokens are
  persisted and the API client refreshes them transparently on a 401.
- **Ride** (`/ride`) — the centrepiece. Choose a route, see a fare per vehicle
  and the current surge, pick vehicle / payment / pooling / promo, then request.
  Once a ride is active, a live console tracks it over a WebSocket
  (`/ws/rides/{id}`): status timeline, driver card, the driver's position moving
  on the map, and a receipt plus star rating at the end.
- **Wallet** (`/wallet`) — balance, one-tap top-ups, and the ledger activity
  feed.
- **History** (`/history`) — past rides with fares and statuses.
- **Console** (`/admin`) — platform metrics from the ledger (admins only).

## Structure

```
src/
  lib/        types (mirror backend schemas), API client (typed, auto-refresh),
              auth context, useRideSocket (WebSocket), fare projection, formatters
  components/ UI primitives, Logo, Nav, DispatchMap (SVG), Telemetry, RideTimeline
  app/        landing, login, register, and the authed (app) group with a route guard
```

The map is a self-contained SVG that projects lat/lng to a viewport, so it needs
no tile server and always renders. The projection is isolated in `Map.tsx`;
swapping in react-leaflet with OpenStreetMap tiles would be a contained change.

## Run it

```bash
cp .env.local.example .env.local   # point at your backend
npm install
npm run dev                        # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_WS_BASE` to your running backend
(`docker compose up` in `../backend` exposes `http://localhost:8000`).

```bash
npm run build       # production build
npm run typecheck   # tsc --noEmit
```

> Fonts load at runtime via a stylesheet link, so builds don't need network
> access to Google Fonts. Switch to `next/font/google` to self-host them.
