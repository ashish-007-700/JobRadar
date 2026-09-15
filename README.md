# JobRadar

JobRadar is a personal job-post aggregation application. It will read job postings from
configured Telegram channels, resolve each posting's final application URL, and display the
results in a React dashboard.

See [`docs/spec.md`](docs/spec.md) for the full project specification.

## Progress

- **Section 1 — Project setup:** React + Vite + Tailwind frontend shell, FastAPI backend with
  a health-check endpoint, CORS restricted to the Vite dev origin, environment variable
  structure for both apps.
- **Section 2 — Supabase setup:** Postgres schema for `channels`, `jobs`, and `fetch_runs`
  (see `supabase/schema.sql`), and a backend Supabase client service with a DB connectivity
  check at `/api/health/db`.

Telegram authentication/fetching, job extraction, URL resolution, and channel/job CRUD are
**not** implemented yet — they belong to later sections.

## Required software

- Python 3.11+
- Node.js 18+ and npm

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
copy .env.example .env       # Windows; use `cp` on macOS/Linux
```

Run it:

```bash
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/api/health` → `{"status": "ok"}`

## Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. In the Supabase dashboard's SQL Editor, run `supabase/schema.sql` from this repo. It
   creates the `channels`, `jobs`, and `fetch_runs` tables used by the rest of the app.
3. In **Project Settings → API**, copy the Project URL and an API key.
4. Add them to `backend/.env`:

   ```text
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-api-key
   ```
5. Restart the backend and check `GET http://localhost:8000/api/health/db` →
   `{"status": "ok"}`. If it returns `{"status": "error", "detail": "..."}`, the message
   explains what's missing (env vars not set, schema not applied, etc.).

## Frontend setup

```bash
cd frontend
npm install
copy .env.example .env       # Windows; use `cp` on macOS/Linux
```

Run it:

```bash
npm run dev
```

Opens on `http://localhost:5173`. The dashboard calls the backend's `/api/health` endpoint
(via `frontend/src/services/api.js`, using the `VITE_API_BASE_URL` env variable) and shows
whether the backend is connected.

## Environment variables

`backend/.env.example`:

```text
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_URL=http://localhost:5173
SUPABASE_URL=
SUPABASE_KEY=
```

`frontend/.env.example`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Never commit real `.env` files — only the `.env.example` templates are tracked.
