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
  `fetch_runs`, and a Fetch Test tab lets you try it from the UI.
- **Section 6 — Job detection & extraction:** Deterministic, rule-based detection of which
  fetched messages are genuine job posts, plus extraction of structured fields (company,
  title, location, experience, qualification, batch, salary, skills, employment type,
  original apply URL). Detected jobs are returned by the fetch endpoint but **not** saved to
  Supabase yet.
- **Section 7 — Application URL resolver:** Follows a job's `original_apply_url` through
  intermediate pages (HTTP redirects, HTML apply-link following, a Playwright fallback for
  JS-heavy pages) to a likely `final_apply_url`, with depth/loop limits and basic SSRF
  protection. Exposed standalone at `POST /api/resolve-url`, and optionally wired into
  `POST /api/telegram/fetch` via `resolve_urls: true`.
- **Section 8 — Job storage:** Detected jobs can be persisted to the existing Supabase `jobs`
  table (opt-in via `save_jobs: true` on the fetch endpoint), with `GET /api/jobs`
  (filterable by date/company/location) and `GET /api/jobs/{id}` to read them back.
- **Section 9 — React dashboard:** The Dashboard tab is now the real day-to-day tool: a date
  picker + "Fetch Messages" (runs fetch → detect → resolve → save in one call and refreshes
  the list), a live Telegram status indicator, real summary counts, company/location
  (server-side) and experience/employment-type (client-side) filters, and job cards with an
  Apply button (`final_apply_url`, falling back to `original_apply_url`) plus an expandable
  details view. The old standalone "Jobs" tab was folded into the Dashboard; a "Debug: Fetch
  Test" tab remains for inspecting raw messages/per-channel results while tuning detection.

Deduplication and scheduling are **not** implemented yet.

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

## Message fetching & job detection (testing only)

`POST /api/telegram/fetch` retrieves messages for a given date from all **enabled** channels,
then runs each message through deterministic, rule-based job detection (see
`backend/app/services/job_detection.py`). Nothing is saved to Supabase yet — this endpoint is
for verifying the pipeline.

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
  "jobs_detected": 12,
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
  ],
  "jobs": [
    {
      "company": "Clarivate",
      "title": "Associate STEM Content Analyst (Engineering)",
      "location": "Chennai (Hybrid)",
      "experience": "Freshers / 0-1 Year",
      "qualification": "B.Sc/M.Sc - Mathematics, Physics, Computer Science, BCA/MCA",
      "batch": "2025 / 2026",
      "salary": "Up to ₹6 LPA",
      "skills": null,
      "employment_type": null,
      "original_apply_url": "https://www.fresheroffcampus.com/clarivate-off-campus/",
      "final_apply_url": null,
      "telegram_message_id": 123,
      "telegram_channel": "fresheroffcampus",
      "telegram_message_url": "https://t.me/fresheroffcampus/123",
      "posted_at": "2026-09-15T09:00:00+00:00"
    }
  ]
}
```

A failing channel is reported in `channel_results` with `status: "error"` and does not stop
the rest of the fetch. Every call is also logged as a row in `fetch_runs` (status
`completed`, `completed_with_errors`, or `failed`, with `jobs_detected` now populated and
`jobs_saved` left at 0 until Section 8).

Job detection is deterministic/rule-based (keyword + structured-field scoring), not an LLM —
see `backend/app/services/job_detection.py` if you want to tune the keyword lists or
threshold. Run its test suite from `backend/` (venv active, `pip install -r
requirements-dev.txt` once):

```bash
pytest tests/test_job_detection.py -v
```

Use the **Fetch Test** tab in the frontend to pick a date, run a fetch, see per-channel
counts, browse detected jobs as cards, and expand each job's (or any raw message's) full JSON
for debugging. Check "Resolve apply URLs" there to also run each detected job's
`original_apply_url` through the resolver below (slower, since it makes real HTTP requests).

## Application URL resolver

Given a job's initial "Apply Now" link, `backend/app/services/url_resolver.py` follows HTTP
redirects and HTML "Apply"-style links (via httpx + BeautifulSoup) — falling back to
Playwright only when a page looks JS-rendered (little visible text, several `<script>` tags
and no plain links) — until it reaches a page with no further application link, or a
configurable hop limit (`MAX_RESOLUTION_DEPTH`, default 5) is hit.

Test it directly, independent of Telegram/Supabase:

```bash
curl -X POST http://localhost:8000/api/resolve-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.fresheroffcampus.com/clarivate-off-campus/"}'
```

Response shape:

```json
{
  "original_apply_url": "https://www.fresheroffcampus.com/clarivate-off-campus/",
  "final_apply_url": "https://careers.clarivate.com/job/12345",
  "resolution_status": "resolved",
  "redirect_chain": ["https://www.fresheroffcampus.com/clarivate-off-campus/", "..."],
  "steps_followed": 1,
  "error": null,
  "final_url_confidence": "high"
}
```

`resolution_status` is one of `resolved`, `no_next_link` (stopped at the original URL — no
apply link was found on it), `max_depth_reached`, `loop_detected`, `http_error`, `timeout`,
`blocked` (SSRF guard), `invalid_url`, or `resolution_error`. `final_url_confidence` is
`"high"` when the final URL looks like a known ATS (Greenhouse, Lever, Workday, etc.) or a
`careers.*`/`jobs.*` domain, `"low"` otherwise — this is a heuristic, not a guarantee.

Run its test suite (mocks all HTTP with `httpx.MockTransport`, so no real network calls or a
Playwright browser install are needed):

```bash
pytest tests/test_url_resolver.py -v
```

**Playwright browser (optional):** the JS-rendering fallback only activates for pages that
look script-heavy with no real content; without a browser installed it just skips that step
and stops at `no_next_link` instead of erroring. To enable it:

```bash
playwright install chromium
```

**Known limitations:**

- SSRF protection blocks literal localhost/private/loopback IPs and `.local` hostnames, but
  does **not** resolve DNS — a public hostname that resolves to a private IP (DNS rebinding)
  is not caught. Acceptable for this personal, non-public-facing app; revisit if it's ever
  exposed beyond localhost.
- Company/apply-link heuristics are tuned against representative examples, not your actual
  channels — expect to adjust `STRONG_APPLY_PHRASES`/`AVOID_TEXT_KEYWORDS`/`KNOWN_ATS_DOMAINS`
  once you see it running against real intermediate sites.
- `original_apply_url` resolution is sequential per fetch call (one job after another), which
  is fine at personal-project volume but would need batching/concurrency at larger scale.

## Job storage

The `jobs` table already had every column the job pipeline produces (created back in Section
2/4) — no schema changes were needed for this section.

`POST /api/telegram/fetch` accepts a `save_jobs: true` flag; when set, every successfully
detected job (after optional URL resolution) is inserted into Supabase individually. A job
that fails to save (bad data, Supabase hiccup) is recorded in that job's `saved: false` and in
the fetch's `errors`, but does **not** stop the rest of the batch — verified with a test where
one job out of three fails to insert while the other two still succeed. `fetch_runs.jobs_saved`
reflects how many actually persisted.

```bash
curl -X POST http://localhost:8000/api/telegram/fetch \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-09-15", "resolve_urls": true, "save_jobs": true}'
```

Read them back:

```bash
curl "http://localhost:8000/api/jobs?date=2026-09-15&company=Clarivate&location=Chennai"
curl http://localhost:8000/api/jobs/<job-id>
```

`GET /api/jobs` filters by `date` (matched against `posted_at`'s day), `company` and
`location` (case-insensitive partial match), and supports `limit`/`offset` pagination.
`GET /api/jobs/{id}` returns 404 if the job doesn't exist.

`original_apply_url` and `final_apply_url` are always stored as separate columns — saving
never overwrites one with the other, and `null` is stored (not a guessed value) for anything
extraction couldn't determine. No deduplication is performed: fetching and saving the same
message twice inserts two rows (the `content_hash` column exists in the schema but is
intentionally unused until a future section).

Run the storage tests (mocked Supabase client, no credentials needed):

```bash
pytest tests/test_job_service.py tests/test_message_service_storage.py tests/test_jobs_api.py -v
```

Use the **Jobs** tab in the frontend to browse persisted jobs with date/company/location
filters. The **Fetch Test** tab has a "Save detected jobs to the database" checkbox so you can
persist jobs from a real fetch run.

**Known limitations:** filtering by `date` matches `posted_at` (the Telegram message's
timestamp), not `discovered_at` (when JobRadar fetched it) — for the vast majority of cases
these are the same day, but a message fetched shortly after midnight could technically have a
`posted_at` from the previous day.

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

Opens on `http://localhost:5173`. All backend calls go through `frontend/src/services/api.js`
(using the `VITE_API_BASE_URL` env variable) — no raw `fetch()` calls in components.

### Dashboard tab

The primary workflow: pick a date, click **Fetch Messages** (runs the full
fetch → detect → resolve → save pipeline and reloads the jobs list), then browse job cards —
click **View details** for the full extracted fields, Telegram source link, and both apply
URLs, or **Apply Now** to open `final_apply_url` (falling back to `original_apply_url`) in a
new tab. The header shows a live Telegram connection dot; when disconnected it tells you to
run the login script rather than trying to authenticate from the browser. Company/location
filters query the API directly; experience/employment-type filters narrow the already-loaded
list client-side (the jobs API doesn't support server-side filtering on those fields).

### Channels tab

Unchanged from Section 4 — add/enable/disable/revalidate/delete Telegram channels.

### Debug: Fetch Test tab

Unchanged from Sections 5-7 — lets you inspect raw fetched messages, per-channel
success/failure, and toggle URL resolution independently of saving. Useful while tuning the
job-detection/resolver heuristics against real channel data.

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
MAX_RESOLUTION_DEPTH=5
```

`frontend/.env.example`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Never commit real `.env` files — only the `.env.example` templates are tracked.
