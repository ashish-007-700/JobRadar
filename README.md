# JobRadar

JobRadar is a personal job-post aggregation application. It will read job postings from
configured Telegram channels, resolve each posting's final application URL, and display the
results in a React dashboard.

See [`docs/spec.md`](docs/spec.md) for the full project specification.

## Section 1 scope

This is the initial project setup only:

- React + Vite + Tailwind frontend shell
- FastAPI backend with a health-check endpoint
- Frontend-to-backend communication over HTTP, with CORS restricted to the Vite dev origin
- Environment variable structure for both apps

Telegram, Supabase, web scraping, and job-fetching logic are **not** implemented yet — they
belong to later sections.

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
```

`frontend/.env.example`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Never commit real `.env` files — only the `.env.example` templates are tracked.
