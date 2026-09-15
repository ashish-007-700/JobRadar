# JobRadar

## 1. Project purpose

JobRadar is a **personal** job-post aggregation tool. It reads job postings from Telegram
channels you configure, follows each posting's "Apply Now" link through any intermediate
pages to find the real application URL, and shows the results in a small React dashboard so
you can review and apply without opening Telegram at all.

It is not a SaaS product: there's no multi-user support, no public sign-up, and no
authentication layer — it's meant to run on your own machine for your own job search.

Full pipeline:

```text
Telegram channels
      ↓
Telethon fetches messages for a date
      ↓
Deterministic rule-based job detection
      ↓
Field extraction (title, company, location, salary, ...)
      ↓
Application URL resolution (redirects, HTML links, JS fallback)
      ↓
Supabase storage
      ↓
React dashboard — review and Apply
```

See [`docs/spec.md`](docs/spec.md) for the original, detailed project specification this was
built against.

## 2. Technology stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Telegram | Telethon (user-account API, not a bot) |
| Web retrieval | httpx, BeautifulSoup |
| Browser automation | Playwright (fallback only, for JS-heavy pages) |
| Database | Supabase (PostgreSQL) |
| Testing | pytest, pytest-asyncio |

## 3. Project structure

```text
jobradar/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app, CORS, lifespan, routers
│   │   ├── config.py                Env var loading
│   │   ├── telegram_login.py        One-time interactive Telegram login (CLI)
│   │   ├── api/routes/              health, channels, telegram, resolver, jobs, fetch_runs
│   │   └── services/                One module per concern:
│   │       ├── supabase_client.py     Lazy Supabase client
│   │       ├── telegram_client.py     Lazy Telethon client + connection lifecycle
│   │       ├── channel_service.py     Channel CRUD + Telegram validation
│   │       ├── message_service.py     Fetch orchestration, fetch_runs, concurrency guard
│   │       ├── job_detection.py       Rule-based job detection + field extraction
│   │       ├── url_resolver.py        Application URL resolution (httpx/BS4/Playwright)
│   │       ├── job_service.py         Job persistence + retrieval
│   │       └── fetch_run_service.py   Fetch history retrieval
│   ├── tests/                       pytest suite (mocked Supabase/Telegram/HTTP — no
│   │                                 real credentials required)
│   ├── requirements.txt             Runtime dependencies
│   └── requirements-dev.txt         + pytest/pytest-asyncio
├── frontend/
│   └── src/
│       ├── pages/                   Dashboard, Channels, FetchHistory, FetchTest (debug)
│       ├── components/              Header, JobCard, JobFilters, SummaryStats,
│       │                            FetchStatusPanel, TelegramStatus
│       ├── services/api.js          The only place that calls the backend
│       └── utils/date.js            Local-timezone date helper
├── supabase/
│   ├── schema.sql                   Full current schema (fresh projects run this)
│   └── migrations/                  Incremental changes for already-created projects
└── docs/spec.md                     Original project specification
```

## 4. Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- A Telegram account (JobRadar logs in as *you*, not as a bot)
- A free [Supabase](https://supabase.com) project

## 5. Environment variables

`backend/.env.example` (copy to `backend/.env` and fill in):

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

| Variable | Purpose |
|---|---|
| `BACKEND_HOST` / `BACKEND_PORT` | Where uvicorn listens |
| `FRONTEND_URL` | The **only** origin allowed by CORS — must match where the frontend runs |
| `SUPABASE_URL` / `SUPABASE_KEY` | Your Supabase project — see §6 |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` / `TELEGRAM_PHONE` | Your Telegram API credentials — see §7 |
| `TELEGRAM_SESSION_NAME` | Base filename for the saved Telethon session |
| `APP_TIMEZONE` | IANA timezone (e.g. `Asia/Kolkata`) used to interpret "today"/a requested date — see §12 |
| `MAX_RESOLUTION_DEPTH` | Max hops the URL resolver will follow (see §13) |

`frontend/.env.example` (copy to `frontend/.env`):

```text
VITE_API_BASE_URL=http://localhost:8000
```

Never commit real `.env` files — only the `.env.example` templates are tracked (`.gitignore`
enforces this; see §16).

## 6. Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. In the Supabase dashboard's **SQL Editor**, run `supabase/schema.sql` from this repo. It
   creates the `channels`, `jobs`, and `fetch_runs` tables everything else depends on.
   - If you created your project before this README's current state and already ran an older
     copy of `schema.sql`, also run `supabase/migrations/0002_add_telegram_channel_id.sql`.
     A brand-new project only needs the current `schema.sql`.
3. In **Project Settings → API**, copy the **Project URL** exactly (it's
   `https://<20-char-id>.supabase.co` — a partial copy/paste here is a common mistake and
   causes a DNS failure that can surface as a confusing "Invalid API key" error instead).
   Copy the **secret key** for `SUPABASE_KEY` (Supabase's current name for what used to be
   called `service_role` — used only server-side, and it bypasses Row Level Security policies
   you haven't configured).
4. Put them in `backend/.env` as `SUPABASE_URL` / `SUPABASE_KEY`.
5. After starting the backend (§9), check `GET http://localhost:8000/api/health/db` →
   `{"status": "ok"}`. An `{"status": "error", "detail": "..."}` response explains what's
   still missing.

**If you get `{"status": "error", "detail": "Invalid API key"}` even with a correct key:**
newer Supabase projects issue keys in a new format (`sb_secret_...`/`sb_publishable_...`,
no dots) instead of the old JWT format (`eyJ...header.payload.signature`). The `supabase`
Python package needs to be **2.31.0 or newer** to accept the new format — older versions
validate the key against a JWT-shaped regex client-side and reject anything else before ever
making a network call, regardless of whether the key is actually valid. This repo pins
`supabase==2.31.0` in `requirements.txt` for exactly this reason; if you're on an older
install, `pip install --upgrade supabase` and re-run `pip install -r requirements.txt`.

## 7. Telegram API setup

JobRadar connects to Telegram as your own user account (via [Telethon](https://docs.telethon.dev)),
not as a bot — this is what lets it read channels you're a member of.

1. Go to [my.telegram.org](https://my.telegram.org) → **API development tools** and create an
   app. This gives you an `api_id` and `api_hash`.
2. Put them in `backend/.env` along with your phone number (international format):

   ```text
   TELEGRAM_API_ID=123456
   TELEGRAM_API_HASH=your-api-hash
   TELEGRAM_PHONE=+1234567890
   ```

**Security precautions:** treat `api_hash` like a password — never paste it into a chat,
issue, or commit. It's excluded from `.env` (never committed) and never logged or returned by
any API response.

## 8. Telegram authentication

The API credentials alone don't log you in — you do that once, interactively:

1. From the `backend/` directory, with the virtualenv active:

   ```bash
   python -m app.telegram_login
   ```

2. It prompts on the **console** (not through the API or frontend) for the login code
   Telegram sends you, and for your 2FA password if you have one enabled.
3. On success, it saves a session file at `backend/<TELEGRAM_SESSION_NAME>.session` (e.g.
   `backend/jobradar.session`). This file is git-ignored and **must never be committed or
   shared** — anyone holding it can act as your Telegram account without needing the login
   code again. Treat it like a password: if you suspect it leaked, delete it and re-run the
   login.
4. Every subsequent backend start reuses this session automatically — you won't be asked to
   log in again unless the file is deleted or Telegram invalidates it.
5. Verify with `GET http://localhost:8000/api/health/telegram`:

   ```json
   { "connected": true, "authenticated": true, "user": "your_username" }
   ```

   If credentials are missing, unauthenticated, or Telegram is unreachable, this returns
   `{"connected": false, "authenticated": false, "detail": "..."}` — the backend keeps running
   either way, it just can't fetch until this is fixed.

## 9. Running the backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
copy .env.example .env       # Windows; use `cp` on macOS/Linux — then fill it in (§5-8)
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/api/health` → `{"status": "ok"}`. The backend starts
successfully even before Supabase/Telegram are configured — those features just report a
clear error (503) until you finish setup.

Optional, only needed for the URL resolver's JS-page fallback (§13):

```bash
playwright install chromium
```

## 10. Running the frontend

```bash
cd frontend
npm install
copy .env.example .env       # Windows; use `cp` on macOS/Linux
npm run dev
```

Opens on `http://localhost:5173`. All backend calls go through `frontend/src/services/api.js`
— there are no raw `fetch()` calls in components.

Four tabs:

- **Dashboard** — the daily-use screen: pick a date, click **Fetch Messages**, browse job
  cards, click **Apply Now**. See §12.
- **Channels** — add/enable/disable/revalidate/delete the Telegram channels JobRadar reads
  from. See §11.
- **Fetch History** — a table of recent fetch runs with per-run error detail.
- **Debug: Fetch Test** — inspects raw fetched messages and per-channel results independent
  of saving; useful while tuning detection/resolution against your actual channels.

## 11. Adding Telegram channels

Once Supabase and Telegram auth are both set up, use the **Channels** tab (or the API
directly):

- `GET /api/channels` — list configured channels.
- `POST /api/channels` `{"channel": "@fresheroffcampus"}` — accepts `@username`, `username`,
  `https://t.me/username`, or `https://t.me/s/username`. The backend resolves it through
  Telethon and only stores it if the channel exists and your account can access it — nothing
  is saved on failure.
- `PUT /api/channels/{id}` `{"enabled": false}` — enable/disable without deleting.
- `DELETE /api/channels/{id}` — remove a channel.
- `POST /api/channels/{id}/validate` — re-checks a stored channel against Telegram and
  refreshes its name/ID if they changed.

Only `enabled` channels are read during a fetch. All Telegram interaction stays in the
backend — the frontend never sees API credentials or session data.

## 12. Fetching jobs

Click **Fetch Messages** on the Dashboard for the selected date, or call the API directly:

```bash
curl -X POST http://localhost:8000/api/telegram/fetch \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-09-15", "resolve_urls": true, "save_jobs": true}'
```

Omit `date` (or send `{}`) to use today, interpreted in `APP_TIMEZONE` — set this to your own
IANA timezone (e.g. `Asia/Kolkata`) so "today" and message-to-day assignment match your local
calendar day rather than UTC's; a message posted just after local midnight would otherwise be
assigned to the wrong day. `resolve_urls`/`save_jobs` default to `false` so the **Debug: Fetch
Test** tab can dry-run the pipeline without writing to Supabase or making slow outbound
requests; the Dashboard always passes both as `true`.

Response:

```json
{
  "date": "2026-09-15",
  "status": "completed",
  "channels_processed": 3,
  "messages_found": 47,
  "jobs_detected": 12,
  "jobs_saved": 12,
  "errors": [],
  "channel_results": [
    { "channel_username": "fresheroffcampus", "messages_processed": 21, "status": "ok", "jobs_detected": 5, "jobs_saved": 5 },
    { "channel_username": "offcampus_jobs", "messages_processed": 0, "status": "error", "error": "Unable to access channel @offcampus_jobs.", "jobs_detected": 0, "jobs_saved": 0 }
  ],
  "messages": [ { "message_id": 123, "channel_id": -1001234567890, "channel_username": "fresheroffcampus", "message_text": "...", "message_date": "2026-09-15T09:00:00+00:00", "message_url": "https://t.me/fresheroffcampus/123" } ],
  "jobs": [ { "company": "Clarivate", "title": "Associate STEM Content Analyst (Engineering)", "location": "Chennai (Hybrid)", "experience": "Freshers / 0-1 Year", "qualification": "B.Sc/M.Sc - Mathematics, Physics, Computer Science, BCA/MCA", "batch": "2025 / 2026", "salary": "Up to ₹6 LPA", "skills": null, "employment_type": null, "original_apply_url": "https://www.fresheroffcampus.com/clarivate-off-campus/", "final_apply_url": "https://careers.clarivate.com/job/12345", "telegram_message_id": 123, "telegram_channel": "fresheroffcampus", "telegram_message_url": "https://t.me/fresheroffcampus/123", "posted_at": "2026-09-15T09:00:00+00:00", "saved": true, "id": "..." } ]
}
```

A failing channel is reported in `channel_results` and does not stop the rest of the fetch; a
job that fails to save is reported the same way (`"saved": false`) without discarding the
others. `status` is `completed`, `completed_with_errors`, or `failed`; every call is also
logged as a row in `fetch_runs`.

**Only one fetch runs at a time** (a process-local guard — this is a single-instance personal
app, not a distributed system). A second request while one is running gets:

```json
{"detail": "A fetch is already running. Please wait for it to finish."}
```
with `409 Conflict`. Check the current/last state at any time — useful after a page reload,
since the frontend can't otherwise tell if a fetch it started is still running:

```bash
curl http://localhost:8000/api/telegram/fetch/status
```

`state` is `idle` (nothing has run yet), `running`, `completed`, `partial`
(`completed_with_errors`), or `failed`. List recent runs (also shown in the **Fetch History**
tab):

```bash
curl "http://localhost:8000/api/fetch-runs?limit=10"
```

Job detection (`backend/app/services/job_detection.py`) is deterministic and rule-based — a
keyword + structured-field scoring function, not an LLM. Errors surfaced anywhere in this
pipeline are converted to plain language before reaching the API (e.g. `"Unable to access
channel @example."`, `"Telegram authentication is unavailable. Run the login script
first."`, `"Timed out while resolving an application URL."`) — raw exceptions stay in the
backend logs only.

Read saved jobs back, with filtering:

```bash
curl "http://localhost:8000/api/jobs?date=2026-09-15&company=Clarivate&location=Chennai"
curl http://localhost:8000/api/jobs/<job-id>
```

`date` matches a job's `posted_at` day; `company`/`location` are case-insensitive partial
matches; `limit`/`offset` paginate. `GET /api/jobs/{id}` returns 404 for a missing job, 400
for a malformed id. `original_apply_url` and `final_apply_url` are always stored as separate
columns — saving never overwrites one with the other, and missing fields are stored as `null`
rather than guessed.

**Deduplication:** before saving a detected job, the backend checks whether a job with the
same `telegram_channel` + `telegram_message_id` already exists (`job_service.job_exists()`)
and skips it if so — the job is reported as `"saved": false, "duplicate": true` in the
response rather than being silently dropped or re-inserted. This is an application-level
check (a `SELECT` before the `INSERT`), not a database unique constraint or an upsert — kept
intentionally simple. It only catches the *same* Telegram message fetched twice; it does
**not** detect the same job posted independently across multiple channels, or reposted with
different wording (that kind of cross-channel/fuzzy dedup remains out of scope). The schema's
`content_hash` column still exists but is unused.

## 13. Understanding the application URL resolver

Given a job's initial "Apply Now" link, `backend/app/services/url_resolver.py` follows the
chain to what's likely the real employer application page:

1. Fetches the URL over HTTP, following redirects **manually** (not via a library flag) so
   every redirect target — not just the starting URL — is checked against the SSRF guard
   below before being fetched.
2. Parses the HTML with BeautifulSoup, looking for `<a>`/`<form>` elements with
   application-related text (`Apply Now`, `Apply Here`, `Careers`, ...), ranked by how
   strong/specific the wording is, while ignoring social-media links and nav/legal text
   (WhatsApp, Telegram, "privacy", "home", ...).
3. If the page looks JavaScript-rendered (very little visible text plus several `<script>`
   tags and no real links) **and only then**, falls back to rendering it with Playwright and
   re-scanning the result. Playwright is never the default path for a normal page.
4. Repeats until it finds a page with no further application link, or hits
   `MAX_RESOLUTION_DEPTH` hops (default 5, configurable), a URL loop, a timeout, or an unsafe
   redirect target.

Test it directly, independent of Telegram/Supabase:

```bash
curl -X POST http://localhost:8000/api/resolve-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.fresheroffcampus.com/clarivate-off-campus/"}'
```

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

`resolution_status`: `resolved` (followed one or more hops to a stable page), `no_next_link`
(the *original* URL had no apply link — nothing to follow), `max_depth_reached`,
`loop_detected`, `http_error`, `timeout`, `blocked` (SSRF guard tripped), `invalid_url`, or
`resolution_error`. `final_url_confidence` is `"high"` when the final URL looks like a known
ATS (Greenhouse, Lever, Workday, ...) or a `careers.*`/`jobs.*` domain, `"low"` otherwise —
a heuristic, not a guarantee; the resolver deliberately never claims certainty it doesn't have.

Response bodies are capped at 2MB while streaming, and requests use short connect/read
timeouts — a slow or huge page can't hang the resolver indefinitely.

## 14. Running tests

Backend (from `backend/`, venv active):

```bash
pip install -r requirements-dev.txt   # once
pytest                                  # whole suite — no real Telegram/Supabase needed
pytest tests/test_job_detection.py tests/test_job_detection_format_variations.py -v
pytest tests/test_channel_service.py -v
pytest tests/test_url_resolver.py -v
pytest tests/test_job_service.py tests/test_message_service_storage.py tests/test_jobs_api.py -v
pytest tests/test_fetch_controls.py -v
```

Every test mocks Supabase (a hand-rolled fake client in `tests/fakes.py`), Telegram
(`unittest.mock`), and HTTP (`httpx.MockTransport`) — none require real credentials, network
access, or a Playwright browser install.

Frontend (from `frontend/`):

```bash
npm run build   # catches compile errors
npm run lint    # oxlint
```

There is no frontend automated test suite; UI behavior is verified manually against a running
backend (see the acceptance checklist below) and, for API-contract-level correctness, by the
backend's own route-level tests (`test_jobs_api.py`, `test_fetch_controls.py`).

## 15. Known limitations

- **SSRF protection is IP-literal only.** `is_safe_url()` blocks `localhost`, `.local`, and
  literal private/loopback/link-local IPs (including on every redirect hop, not just the
  starting URL), but it does not resolve hostnames — a public hostname that resolves to a
  private IP (DNS rebinding) is not caught. Acceptable for this personal, non-public-facing
  app; revisit before ever exposing it beyond localhost.
- **No authentication anywhere.** Every endpoint (including `/api/resolve-url`, which makes
  arbitrary outbound HTTP requests on request) is reachable by anyone who can reach the
  backend port. This is intentional for a single-user local tool — do not put this backend on
  the open internet without adding auth in front of it.
- **Job detection and URL-resolution heuristics are tuned on synthetic examples**, not your
  actual channels. Expect to adjust `job_detection.py`'s keyword lists/threshold and
  `url_resolver.py`'s `STRONG_APPLY_PHRASES`/`KNOWN_ATS_DOMAINS` after seeing real traffic. A
  known gap: a bare "`<Role> opening at <Company>`" post with no hiring keyword, no labeled
  fields, and no structured context can fall just under the detection threshold — realistic
  posts almost always include at least one labeled field (location/experience/etc.), which
  resolves this in practice.
- **Date filtering uses `posted_at`** (the Telegram message's own timestamp), not
  `discovered_at` (when JobRadar fetched it) — the same day in the vast majority of cases, but
  a message posted just before midnight and fetched just after could land on the "wrong"
  day's filter.
- **The "one fetch at a time" guard is per-process.** Fine for the single-worker setup this
  app assumes; running multiple `uvicorn --workers N` processes would let each enforce it
  independently rather than against each other.
- **Dedup is exact-match only.** It catches the same Telegram message saved twice (by
  `telegram_channel` + `telegram_message_id`), but not the same job posted independently
  across multiple channels or reposted with different wording — see §12.
- **No scheduling.** Fetching is always manually triggered; there is no background/cron job.
- **URL resolution is sequential**, one job after another within a fetch — fine at personal
  volume, would need batching/concurrency at larger scale.
- **No frontend automated tests** — see §14.

## 16. Security notes

- **CORS** is restricted to the single configured `FRONTEND_URL` origin (`allow_origins=[...]`,
  never `["*"]`).
- **Secrets** (`SUPABASE_KEY`, `TELEGRAM_API_HASH`, etc.) live only in `backend/.env`, which is
  git-ignored; nothing in the codebase logs or returns them in an API response (verified: no
  log statement references credentials, session content, login codes, or 2FA passwords).
- **The Telegram session file** (`backend/*.session`) grants full account access without
  needing the login code again — it's git-ignored and was never committed (checked against the
  full git history, not just the current working tree).
- **Errors are converted to plain-language messages** before reaching any API response; raw
  Python exceptions/stack traces are never returned to a client (verified for every route —
  see §2/§12).
- **The URL resolver fetches arbitrary user/Telegram-supplied URLs** by design (that's its
  job). It only allows `http`/`https`, blocks literal localhost/private/loopback targets on
  every hop (including redirects — see §15's DNS-rebinding caveat), caps response size, and
  bounds hops/timeouts so it can't hang or be used to scan your local network via a
  public-looking URL that happens to redirect internally.
- **No authentication layer** exists anywhere in this app (see §15) — this is a deliberate
  scope decision for a personal, localhost-only tool, not an oversight. Do not deploy this
  backend to a shared or public host as-is.
