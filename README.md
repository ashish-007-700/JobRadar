# JobRadar

Personal job-post aggregator that reads job postings from configured Telegram channels,
resolves each posting's final application URL, and displays them in a React dashboard.

See [`docs/spec.md`](docs/spec.md) for the full project specification.

## Project layout

```text
backend/    FastAPI application (Python)
frontend/   React + Vite + Tailwind dashboard
docs/       Project specification
```

## Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env      # fill in Telegram/Supabase credentials later
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/api/health`

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Opens on `http://localhost:5173`. API requests to `/api/*` are proxied to the backend at
`http://localhost:8000` (see `vite.config.js`).

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```text
TELEGRAM_API_ID       # from https://my.telegram.org
TELEGRAM_API_HASH
SUPABASE_URL
SUPABASE_KEY
```

Never commit `.env` files or Telegram `.session` files — both are already git-ignored.

## Status

Section 1 (Project Setup) complete: backend and frontend skeletons run and the frontend
can reach the backend through the dev proxy. Subsequent sections (Supabase setup, Telegram
auth, channel management, fetching, job extraction, URL resolution, dashboard, etc.) follow
the sequence in `docs/spec.md`.
