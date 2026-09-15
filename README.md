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
- **Section 3 — Telegram authentication:** A Telethon-backed service that connects to a
  Telegram user account, persists the session, and reports status at `/api/health/telegram`.

Telegram channel management/fetching, job extraction, URL resolution, and job storage are
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

## Telegram authentication setup

JobRadar connects to Telegram as your own user account (not a bot), using
[Telethon](https://docs.telethon.dev).

1. Get API credentials from [my.telegram.org](https://my.telegram.org) → **API development
   tools**. This gives you an `api_id` and `api_hash`.
2. Add them to `backend/.env`:

   ```text
   TELEGRAM_API_ID=123456
   TELEGRAM_API_HASH=your-api-hash
   TELEGRAM_PHONE=+1234567890
   TELEGRAM_SESSION_NAME=jobradar
   ```
3. Run the one-time interactive login from the `backend/` directory (venv active):

   ```bash
   python -m app.telegram_login
   ```

   It prompts on the console for the login code Telegram sends you, and for your 2FA
   password if you have one enabled. Nothing is sent to or exposed through the API/frontend.
4. This creates a session file at `backend/<TELEGRAM_SESSION_NAME>.session` (e.g.
   `backend/jobradar.session`). It is git-ignored and must never be committed — anyone with
   this file can act as your Telegram account without needing the login code again.
5. On every subsequent backend start, the existing session is reused automatically — you
   won't be asked to log in again unless the session file is deleted or Telegram invalidates
   it.
6. Check `GET http://localhost:8000/api/health/telegram` to confirm:

   ```json
   { "connected": true, "authenticated": true, "user": "your_username" }
   ```

   If credentials are missing or Telegram is unreachable, this returns
   `{"connected": false, "authenticated": false, "detail": "..."}` instead of crashing the
   backend.

**Security precautions:** never commit `.env` or `*.session` files, never paste your API
hash, login code, or 2FA password into a chat or issue, and treat the `.session` file like a
password — delete and re-authenticate if you suspect it leaked.

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
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_PHONE=
TELEGRAM_SESSION_NAME=jobradar
```

`frontend/.env.example`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Never commit real `.env` files — only the `.env.example` templates are tracked.
