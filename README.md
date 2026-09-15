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
- **Section 4 — Channel management:** Full channel CRUD (`/api/channels`) backed by
  Supabase, with each channel validated/resolved against Telegram (via Telethon) before it's
  stored, plus a revalidation endpoint and a Channels tab in the dashboard.
- **Section 5 — Message fetching:** `POST /api/telegram/fetch` retrieves raw Telegram
  messages for a requested date from enabled channels only, records the run in
  `fetch_runs`, and a Fetch Test tab lets you try it from the UI. Messages are **not** yet
  treated as jobs.

Job extraction, URL resolution, and job storage are **not** implemented yet — they belong to
later sections.

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

If you already ran `supabase/schema.sql` before Section 4 was added, also run
`supabase/migrations/0002_add_telegram_channel_id.sql` — it adds the `telegram_channel_id`
column the channels API now relies on. A brand-new project only needs the current
`supabase/schema.sql`.

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

## Channel management

Once Supabase and Telegram authentication are both set up, use the **Channels** tab in the
dashboard (or the API directly) to configure which channels JobRadar reads from:

- `GET /api/channels` — list configured channels.
- `POST /api/channels` `{"channel": "@fresheroffcampus"}` — normalizes the input (accepts
  `@username`, `username`, `https://t.me/username`, or `https://t.me/s/username`), resolves it
  through Telethon, and only stores it in Supabase if the channel exists and is accessible to
  your authenticated Telegram account.
- `PUT /api/channels/{id}` `{"enabled": false}` — enable/disable a channel without deleting it.
- `DELETE /api/channels/{id}` — remove a channel.
- `POST /api/channels/{id}/validate` — re-checks a stored channel against Telegram and
  refreshes its name/ID in Supabase if they changed.

Only `enabled` channels will be used by the future message-fetching pipeline. All Telegram
interaction happens in the backend — the frontend never sees API credentials or session data.

## Message fetching (testing only)

`POST /api/telegram/fetch` retrieves messages for a given date from all **enabled** channels.
This section is retrieval only — no job detection or storage happens yet.

```bash
curl -X POST http://localhost:8000/api/telegram/fetch \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-09-15"}'
```

Omit `date` (or send `{}`/no body) to use today's date, interpreted in the `APP_TIMEZONE`
configured in `backend/.env` (default `UTC`) — set it to your own IANA timezone (e.g.
`Asia/Kolkata`) so "today" matches your local day, not UTC's.

Response shape:

```json
{
  "date": "2026-09-15",
  "channels_processed": 3,
  "messages_found": 47,
  "channel_results": [
    { "channel_username": "fresheroffcampus", "message_count": 21, "status": "ok" },
    { "channel_username": "offcampus_jobs", "message_count": 0, "status": "error", "detail": "..." }
  ],
  "messages": [
    {
      "message_id": 123,
      "channel_id": -1001234567890,
      "channel_username": "fresheroffcampus",
      "message_text": "...",
      "message_date": "2026-09-15T09:00:00+00:00",
      "message_url": "https://t.me/fresheroffcampus/123"
    }
  ]
}
```

A failing channel is reported in `channel_results` with `status: "error"` and does not stop
the rest of the fetch. Every call is also logged as a row in `fetch_runs` (status
`completed`, `completed_with_errors`, or `failed`).

Use the **Fetch Test** tab in the frontend to pick a date, run a fetch, see the per-channel
counts, and expand individual raw messages for debugging.

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
APP_TIMEZONE=UTC
```

`frontend/.env.example`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Never commit real `.env` files — only the `.env.example` templates are tracked.
