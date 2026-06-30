# Shohojatri — Setup Guide

A full-stack ride-hailing app: FastAPI backend + Next.js frontend.
Follow these steps exactly and it will run.

---

## What's in this folder

```
shohojatri/
├── backend/      ← Python API (FastAPI + PostgreSQL + Redis)
├── frontend/     ← Web app (Next.js + TypeScript)
└── README.md     ← this file
```

---

## Before you start — install these two things

### 1. Docker Desktop
This starts the database and backend automatically.
Download: https://www.docker.com/products/docker-desktop/
→ Install it, open it, make sure it's running (whale icon in your taskbar).

### 2. Node.js (for the frontend)
Download: https://nodejs.org  →  choose the "LTS" version
→ Install it. Restart VSCode after.

---

## Step-by-step

Open VSCode, then open the **shohojatri** folder
(File → Open Folder → select the shohojatri folder you downloaded).

You'll see two sub-folders in the sidebar: `backend/` and `frontend/`.

---

### STEP 1 — Start the backend

Open a terminal in VSCode: **Terminal → New Terminal**

```bash
cd backend
docker-compose up --build
```

**First time only** this downloads PostgreSQL + Redis images (~500 MB) and builds
the Python image. Takes 2–5 minutes. Subsequent starts take ~10 seconds.

You'll know it's ready when you see:
```
api_1  | INFO:     Application startup complete.
```

✅ Check it works: open http://localhost:8000/docs in your browser.
   You should see the Swagger API docs page.

> Leave this terminal running. Open a second terminal for the next step.

---

### STEP 2 — Start the frontend

Open a **second terminal** in VSCode (click the + icon in the terminal panel):

```bash
cd frontend
npm install
npm run dev
```

`npm install` takes ~30 seconds the first time (downloads packages).
`npm run dev` starts the web app.

You'll know it's ready when you see:
```
▲ Next.js ready on http://localhost:3000
```

✅ Open http://localhost:3000 in your browser. You should see the Shohojatri landing page.

---

### STEP 3 — Try it out

1. Click **Get started** → fill in the registration form → you're in.
2. On the **Ride** page, pick a pickup and drop-off, choose a vehicle, click **Request**.
3. The page switches to the **live console** — status timeline, fare telemetry, driver ping.
4. Check **Wallet** to see your balance (top up with the quick buttons).
5. Check **History** to see your past rides.

---

### Making admin features work (optional)

The **Console** tab (admin metrics) requires an admin account. To promote yourself:

1. Register a normal account on the app.
2. Open a new terminal and run:

```bash
curl -s -X POST http://localhost:8000/api/v1/admin/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","secret":"admin-secret-local"}' | python3 -m json.tool
```

3. Sign out and sign back in — the **Console** tab appears in the nav.

---

## Stopping everything

- Frontend: press `Ctrl + C` in the frontend terminal.
- Backend: press `Ctrl + C` in the backend terminal, then run `docker-compose down`.

---

## If something goes wrong

**Port already in use (backend)**
```bash
docker-compose down
docker-compose up --build
```

**Port already in use (frontend)**
```bash
npm run dev -- -p 3001
```
Then open http://localhost:3001 instead.

**Backend shows database errors on first start**
The database might still be initialising. Wait 10 seconds and refresh.

**`npm install` fails**
Make sure Node.js is installed: open a terminal and type `node --version`.
It should print something like `v20.x.x`.

---

## Folder structure at a glance

```
backend/
├── app/
│   ├── api/          ← HTTP endpoints
│   ├── core/         ← config, auth, middleware
│   ├── models/       ← database models
│   ├── services/     ← business logic
│   └── ws/           ← WebSocket hub
├── alembic/          ← database migrations
├── tests/            ← 50 passing tests
├── docker-compose.yml
└── .env              ← already filled in for local use

frontend/
├── src/
│   ├── app/          ← pages (Next.js App Router)
│   ├── components/   ← UI: Map, Telemetry, Timeline, Nav...
│   └── lib/          ← API client, auth, types, WebSocket hook
├── .env.local        ← already filled in for local use
└── package.json
```
