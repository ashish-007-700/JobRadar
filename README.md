<div align="center">

# 🎯 JobRadar

**Your personal job-post aggregation tool — from Telegram channels to a clean dashboard.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org/)

---

</div>

## 📋 Table of Contents

- [About](#-about)
- [How It Works](#-how-it-works)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Getting Started](#-getting-started)
  - [Environment Variables](#1-environment-variables)
  - [Supabase Setup](#2-supabase-setup)
  - [Telegram API Setup](#3-telegram-api-setup)
  - [Telegram Authentication](#4-telegram-authentication)
  - [Running the Backend](#5-running-the-backend)
  - [Running the Frontend](#6-running-the-frontend)
- [Usage Guide](#-usage-guide)
  - [Adding Channels](#adding-telegram-channels)
  - [Fetching Jobs](#fetching-jobs)
  - [URL Resolver](#understanding-the-url-resolver)
- [Running Tests](#-running-tests)
- [Known Limitations](#-known-limitations)
- [Security Notes](#-security-notes)

---

## 🔍 About

JobRadar reads job postings from Telegram channels you configure, follows each posting's "Apply Now" link through any intermediate pages to find the **real application URL**, and shows the results in a React dashboard so you can review and apply without opening Telegram at all.

> [!NOTE]
> This is **not** a SaaS product — there's no multi-user support, no public sign-up, and no authentication layer. It's meant to run on **your own machine** for **your own job search**.

---

## ⚙️ How It Works

```
┌─────────────────────┐
│  Telegram Channels   │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Telethon Fetches    │  ← Fetches messages for a given date
│  Messages            │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Job Detection       │  ← Deterministic, rule-based detection
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Field Extraction    │  ← Title, company, location, salary, ...
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  URL Resolution      │  ← Follows redirects, HTML links, JS fallback
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Supabase Storage    │  ← PostgreSQL via Supabase
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  React Dashboard     │  ← Review jobs & Apply
└─────────────────────┘
```

> 📄 See [`docs/spec.md`](docs/spec.md) for the original, detailed project specification.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| **Frontend** | React, Vite, Tailwind CSS | Dashboard UI |
| **Backend** | Python, FastAPI | API server |
| **Telegram** | Telethon | User-account API (not a bot) |
| **Web Retrieval** | httpx, BeautifulSoup | HTTP fetching & HTML parsing |
| **Browser Automation** | Playwright | Fallback only, for JS-heavy pages |
| **Database** | Supabase (PostgreSQL) | Persistent storage |
| **Testing** | pytest, pytest-asyncio | Backend test suite |

---

## 📁 Project Structure

```
JobRadar/
│
├── 📂 backend/
│   ├── 📂 app/
│   │   ├── main.py                  # FastAPI app, CORS, lifespan, routers
│   │   ├── config.py                # Env var loading
│   │   ├── telegram_login.py        # One-time interactive Telegram login (CLI)
│   │   ├── 📂 api/routes/           # health, channels, telegram, resolver, jobs, fetch_runs
│   │   └── 📂 services/
│   │       ├── supabase_client.py   # Lazy Supabase client
│   │       ├── telegram_client.py   # Lazy Telethon client + connection lifecycle
│   │       ├── channel_service.py   # Channel CRUD + Telegram validation
│   │       ├── message_service.py   # Fetch orchestration, fetch_runs, concurrency guard
│   │       ├── job_detection.py     # Rule-based job detection + field extraction
│   │       ├── url_resolver.py      # Application URL resolution (httpx/BS4/Playwright)
│   │       ├── job_service.py       # Job persistence + retrieval
│   │       └── fetch_run_service.py # Fetch history retrieval
│   ├── 📂 tests/                    # Mocked suite — no real credentials required
│   ├── requirements.txt             # Runtime dependencies
│   └── requirements-dev.txt         # + pytest/pytest-asyncio
│
├── 📂 frontend/
│   └── 📂 src/
│       ├── 📂 pages/                # Dashboard, Channels, FetchHistory, FetchTest
│       ├── 📂 components/           # Header, JobCard, JobFilters, SummaryStats, etc.
│       ├── 📂 services/
│       │   └── api.js               # Single API communication layer
│       └── 📂 utils/
│           └── date.js              # Local-timezone date helper
│
├── 📂 supabase/
│   ├── schema.sql                   # Full current schema (fresh projects)
│   └── 📂 migrations/              # Incremental changes for existing projects
│
└── 📂 docs/
    └── spec.md                      # Original project specification
```

---

## ✅ Prerequisites

| Requirement | Version |
|:------------|:--------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | Bundled with Node.js |
| Telegram account | Required (logs in as *you*, not as a bot) |
| Supabase project | Free tier works — [supabase.com](https://supabase.com) |

---

## 🚀 Getting Started

### 1. Environment Variables

<details>
<summary><strong>Backend — <code>backend/.env</code></strong></summary>

Copy `backend/.env.example` to `backend/.env` and fill in the values:

```env
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
|:---------|:--------|
| `BACKEND_HOST` / `BACKEND_PORT` | Where uvicorn listens |
| `FRONTEND_URL` | The **only** origin allowed by CORS — must match where the frontend runs |
| `SUPABASE_URL` / `SUPABASE_KEY` | Your Supabase project credentials |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` / `TELEGRAM_PHONE` | Your Telegram API credentials |
| `TELEGRAM_SESSION_NAME` | Base filename for the saved Telethon session |
| `APP_TIMEZONE` | IANA timezone (e.g. `Asia/Kolkata`) — used to interpret "today" and date assignment |
| `MAX_RESOLUTION_DEPTH` | Max hops the URL resolver will follow (default: 5) |

</details>

<details>
<summary><strong>Frontend — <code>frontend/.env</code></strong></summary>

Copy `frontend/.env.example` to `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

</details>

> [!WARNING]
> Never commit real `.env` files — only the `.env.example` templates are tracked. The `.gitignore` enforces this.

---

### 2. Supabase Setup

1. Create a project at [supabase.com](https://supabase.com).
2. In the Supabase dashboard's **SQL Editor**, run [`supabase/schema.sql`](supabase/schema.sql) from this repo.
   - It creates the `channels`, `jobs`, and `fetch_runs` tables.
   - If upgrading from an older version, also run `supabase/migrations/0002_add_telegram_channel_id.sql`.
3. In **Project Settings → API**, copy:
   - **Project URL** → `SUPABASE_URL`
   - **Secret key** → `SUPABASE_KEY`
4. Put them in `backend/.env`.
5. Verify: `GET http://localhost:8000/api/health/db` → `{"status": "ok"}`

<details>
<summary><strong>⚠️ Troubleshooting: "Invalid API key" error</strong></summary>

Newer Supabase projects issue keys in a new format (`sb_secret_...` / `sb_publishable_...`, no dots) instead of the old JWT format (`eyJ...`). The `supabase` Python package needs to be **≥ 2.31.0** to accept the new format — older versions reject it client-side before making a network call.

This repo pins `supabase==2.31.0` in `requirements.txt`. If you're on an older install:

```bash
pip install --upgrade supabase
pip install -r requirements.txt
```

</details>

---

### 3. Telegram API Setup

JobRadar connects as your **own user account** via [Telethon](https://docs.telethon.dev) — this lets it read channels you're a member of.

1. Go to [my.telegram.org](https://my.telegram.org) → **API development tools** → create an app.
2. Add to `backend/.env`:

   ```env
   TELEGRAM_API_ID=123456
   TELEGRAM_API_HASH=your-api-hash
   TELEGRAM_PHONE=+1234567890
   ```

> [!CAUTION]
> Treat `api_hash` like a password — never paste it into a chat, issue, or commit. It's excluded from `.env` (never committed) and never logged or returned by any API response.

---

### 4. Telegram Authentication

The API credentials alone don't log you in — you do that **once**, interactively:

```bash
cd backend
python -m app.telegram_login
```

- It prompts on the **console** for the login code Telegram sends you (and your 2FA password if enabled).
- On success, it saves a session file at `backend/<TELEGRAM_SESSION_NAME>.session`.
- Subsequent backend starts reuse this session automatically.

> [!CAUTION]
> The session file (`backend/*.session`) grants **full account access** without needing the login code again. It's git-ignored and must **never** be committed or shared. If you suspect it leaked, delete it and re-run the login.

**Verify:**

```bash
GET http://localhost:8000/api/health/telegram
```

```json
{ "connected": true, "authenticated": true, "user": "your_username" }
```

---

### 5. Running the Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env         # Windows (use cp on macOS/Linux) — then fill it in
uvicorn app.main:app --reload
```

**Health check:** `GET http://localhost:8000/api/health` → `{"status": "ok"}`

> [!TIP]
> The backend starts successfully even before Supabase/Telegram are configured — those features just report a clear error (503) until you finish setup.

**Optional** — only needed for the URL resolver's JS-page fallback:

```bash
playwright install chromium
```

---

### 6. Running the Frontend

```bash
cd frontend
npm install
copy .env.example .env         # Windows (use cp on macOS/Linux)
npm run dev
```

Opens on **http://localhost:5173**. All backend calls go through [`frontend/src/services/api.js`](frontend/src/services/api.js).

#### 📑 Dashboard Tabs

| Tab | Description |
|:----|:------------|
| **Dashboard** | Daily-use screen — pick a date, fetch messages, browse job cards, click Apply Now |
| **Channels** | Add / enable / disable / revalidate / delete Telegram channels |
| **Fetch History** | Table of recent fetch runs with per-run error details |
| **Debug: Fetch Test** | Inspect raw fetched messages — useful while tuning detection/resolution |

---

## 📖 Usage Guide

### Adding Telegram Channels

Use the **Channels** tab or the API directly:

| Method | Endpoint | Body / Params |
|:-------|:---------|:--------------|
| **List** | `GET /api/channels` | — |
| **Add** | `POST /api/channels` | `{"channel": "@fresheroffcampus"}` |
| **Toggle** | `PUT /api/channels/{id}` | `{"enabled": false}` |
| **Delete** | `DELETE /api/channels/{id}` | — |
| **Re-validate** | `POST /api/channels/{id}/validate` | — |

> Accepts `@username`, `username`, `https://t.me/username`, or `https://t.me/s/username`. Only stores the channel if it exists and your account can access it.

---

### Fetching Jobs

Click **Fetch Messages** on the Dashboard, or call the API:

```bash
curl -X POST http://localhost:8000/api/telegram/fetch \
  -H "Content-Type: application/json" \
  -d '{"date": "2026-09-15", "resolve_urls": true, "save_jobs": true}'
```

- Omit `date` to use **today** (interpreted in `APP_TIMEZONE`).
- `resolve_urls` / `save_jobs` default to `false` (for dry-run debugging); the Dashboard always sends `true`.

<details>
<summary><strong>📤 Example response</strong></summary>

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
    {
      "channel_username": "fresheroffcampus",
      "messages_processed": 21,
      "status": "ok",
      "jobs_detected": 5,
      "jobs_saved": 5
    }
  ]
}
```

</details>

<details>
<summary><strong>🔄 Concurrency & Status</strong></summary>

**Only one fetch runs at a time.** A second request while one is running returns `409 Conflict`:

```json
{"detail": "A fetch is already running. Please wait for it to finish."}
```

Check the current/last state:

```bash
curl http://localhost:8000/api/telegram/fetch/status
```

States: `idle` | `running` | `completed` | `partial` | `failed`

List recent runs:

```bash
curl "http://localhost:8000/api/fetch-runs?limit=10"
```

</details>

<details>
<summary><strong>🔎 Querying Saved Jobs</strong></summary>

```bash
# Filter by date, company, location
curl "http://localhost:8000/api/jobs?date=2026-09-15&company=Clarivate&location=Chennai"

# Get a specific job
curl http://localhost:8000/api/jobs/<job-id>
```

- `date` matches `posted_at` day
- `company` / `location` are case-insensitive partial matches
- `limit` / `offset` for pagination

</details>

<details>
<summary><strong>🗑️ Deduplication & Clearing</strong></summary>

**Dedup:** Before saving, the backend checks for an existing job with the same `telegram_channel` + `telegram_message_id`. Duplicates are reported as `"saved": false, "duplicate": true`. This is exact-match only — cross-channel or fuzzy dedup is out of scope.

**Clear view button:** Non-destructive — just empties the list in the browser tab. Nothing is deleted from Supabase.

**Permanent delete** (use with care):

```bash
curl -X DELETE "http://localhost:8000/api/jobs?date=2026-09-15"
```

> `date` is a **required** query param to prevent accidentally wiping all jobs. This is a real, permanent delete with no undo.

</details>

---

### Understanding the URL Resolver

The resolver ([`url_resolver.py`](backend/app/services/url_resolver.py)) follows an "Apply Now" link to find the **real employer application page**:

```
1. Fetch URL via HTTP → follow redirects manually (SSRF-checked per hop)
2. Parse HTML → find <a>/<form> with apply-related text (ranked by strength)
3. If page is JS-rendered → Playwright fallback (only when needed)
4. Repeat until stable page, max depth, loop, timeout, or unsafe target
```

**Test it independently:**

```bash
curl -X POST http://localhost:8000/api/resolve-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.fresheroffcampus.com/clarivate-off-campus/"}'
```

<details>
<summary><strong>📤 Example response</strong></summary>

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

**Status values:** `resolved` · `no_next_link` · `max_depth_reached` · `loop_detected` · `http_error` · `timeout` · `blocked` · `invalid_url` · `resolution_error`

**Confidence:** `high` when the final URL matches a known ATS (Greenhouse, Lever, Workday, etc.) or a `careers.*`/`jobs.*` domain; `low` otherwise.

</details>

---

## 🧪 Running Tests

### Backend

```bash
cd backend
pip install -r requirements-dev.txt   # once
pytest                                 # full suite — no real credentials needed
```

<details>
<summary><strong>Run specific test groups</strong></summary>

```bash
# Job detection
pytest tests/test_job_detection.py tests/test_job_detection_format_variations.py -v

# Channel service
pytest tests/test_channel_service.py -v

# URL resolver
pytest tests/test_url_resolver.py -v

# Job persistence & API
pytest tests/test_job_service.py tests/test_message_service_storage.py tests/test_jobs_api.py -v

# Fetch controls
pytest tests/test_fetch_controls.py -v
```

</details>

> All tests mock Supabase, Telegram, and HTTP — none require real credentials, network access, or Playwright.

### Frontend

```bash
cd frontend
npm run build    # catches compile errors
npm run lint     # oxlint
```

> No frontend automated test suite — UI behavior is verified manually against a running backend.

---

## ⚠️ Known Limitations

| Limitation | Details |
|:-----------|:--------|
| **SSRF protection** | IP-literal only — blocks localhost, `.local`, and private IPs on every hop, but doesn't resolve hostnames (DNS rebinding not caught). Acceptable for localhost-only use. |
| **No authentication** | Every endpoint is open. Intentional for single-user local use — do not expose to the internet without auth. |
| **Detection heuristics** | Tuned on synthetic examples — expect to adjust keyword lists/thresholds after seeing real traffic. |
| **Date filtering** | Uses `posted_at` (Telegram timestamp), not `discovered_at` — edge case around midnight. |
| **Concurrency guard** | Per-process only — multiple `uvicorn` workers would each enforce independently. |
| **Dedup** | Exact-match by `telegram_channel` + `telegram_message_id` only — no cross-channel or fuzzy dedup. |
| **No scheduling** | Fetching is always manually triggered. |
| **Sequential URL resolution** | One job at a time within a fetch — fine at personal volume. |
| **No frontend tests** | See [Running Tests](#-running-tests). |

---

## 🔒 Security Notes

- **CORS** is restricted to the single configured `FRONTEND_URL` origin (never `["*"]`).
- **Secrets** (`SUPABASE_KEY`, `TELEGRAM_API_HASH`, etc.) live only in `backend/.env`, which is git-ignored. Nothing in the codebase logs or returns them in API responses.
- **The Telegram session file** grants full account access — it's git-ignored and was never committed (verified against full git history).
- **Errors** are converted to plain-language messages before reaching API responses — raw exceptions/stack traces are never returned to clients.
- **The URL resolver** only allows `http`/`https`, blocks literal localhost/private/loopback targets on every hop, caps response size at 2MB, and bounds hops/timeouts.
- **No authentication layer** exists — this is a deliberate scope decision for a personal, localhost-only tool.

---

<div align="center">

**Built for personal use** · Not a SaaS product · Run it locally, own your job search

</div>