# Deploying Monsoon Decision Twin

**Backend** (FastAPI + Postgres) on **Render** or **Railway**; **frontend** (static Vite build) on **Vercel**.
The app uses synthetic data, so a fresh deploy seeds 10 blocks and 30 panchayats automatically on first start.

## Before you start (limits to know)

- **Officer reviews live in memory.** They're lost on restart or redeploy (free Render instances also sleep and restart), and aren't shared between instances. Keep **one instance, one worker** (the configs below do). Move the review store to Postgres before real use.
- **Use Postgres, not SQLite**, in the cloud: the container disk is wiped on redeploy. Farmer feedback is stored in the database.
- **No authentication yet.** Anyone with the URLs can use the officer dashboard, review queue and feedback admin page. Don't share them publicly.
- WhatsApp sending is **log only** (see `backend/app/services/notify.py`).

## 1. Backend

Either option gives you a URL like `https://monsoon-backend.onrender.com`. Check it with `GET /health`, which should return `"database": {"status": "ok", "dialect": "postgresql"}`.

### Option A: Render (Blueprint)

1. Push the repo to GitHub.
2. Render dashboard → **New → Blueprint** → pick the repo. `render.yaml` creates the web service (`backend/`, health check `/health`) and a Postgres database, and wires up `DATABASE_URL`.
3. When prompted (or later under *Environment*), set:
   - `CORS_ORIGINS`: your Vercel URL, e.g. `https://monsoon-twin.vercel.app` (comma-separate several)
   - `PUBLIC_APP_URL`: the same Vercel URL (used in WhatsApp message links)
   - `CORS_ORIGIN_REGEX` (optional): e.g. `https://monsoon-twin-.*\.vercel\.app` to allow Vercel preview deploys

   You can deploy the backend first with a placeholder and update these after step 2.

### Option B: Railway

1. **New Project → Deploy from GitHub repo**, and set the service's **Root Directory** to `backend`. It builds `backend/Dockerfile` (`railway.json` sets the `/health` health check and a single replica).
2. **+ New → Database → PostgreSQL**. In the backend service's *Variables*, add `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`.
3. Add `CORS_ORIGINS`, `PUBLIC_APP_URL` (and optionally `CORS_ORIGIN_REGEX`) as in Render step 3.
4. *Settings → Networking → Generate Domain* to get the public URL.

Notes for both:
- Both platforms provide `postgres://…` URLs. The backend rewrites these to the psycopg 3 driver automatically.
- `$PORT` is provided by the platform.

## 2. Frontend on Vercel

1. **Add New → Project** → import the repo, and set **Root Directory** to `frontend`. Vercel detects Vite (build `npm run build`, output `dist`).
2. **Environment variable:** `VITE_API_BASE` = your backend URL, e.g. `https://monsoon-backend.onrender.com` (no trailing slash). It's baked in at build time, so **redeploy after changing it**.
3. Deploy. `frontend/vercel.json` rewrites every path to `index.html`, so direct links like `/farmer/GP014` and `/admin/feedback` work.
4. Put the Vercel URL into the backend's `CORS_ORIGINS` and `PUBLIC_APP_URL` (step 1), then redeploy or restart the backend.

## 3. Check it end to end

- `https://<vercel-url>/`: the header shows **Backend ok · postgresql**, the map shows 30 markers, and the review queue lists flagged decisions.
- Click a marker → the detail panel shows a recommendation, the WhatsApp message and a forecast. Approve something in the review queue and its marker updates.
- `https://<vercel-url>/farmer/GP014` on a phone: the advice card and "Why this advice?" work.
- `https://<vercel-url>/admin/feedback`: empty at first. `POST <backend>/feedback` with `{"panchayat_id":"GP014","rain_occurred":true,"action_taken":"sowed"}` makes an entry appear.
- **Errors:**
  - A red "Couldn't load … / Can't reach the server" in the UI usually means `VITE_API_BASE` is wrong or the backend is asleep (the first request on a free plan can take ~30–60 s).
  - A CORS error in the browser console means `CORS_ORIGINS` doesn't exactly match the Vercel URL (scheme, no trailing path).

## Alternative: one server with Docker Compose

On any VM with Docker:

```bash
cp .env.example .env              # set POSTGRES_PASSWORD and PUBLIC_APP_URL
docker compose --profile prod up -d --build web
```

This runs Postgres, the API (internal only) and nginx on `APP_PORT` (default 8080). nginx serves the built frontend and forwards `/api/*` to the API on the same origin, so no CORS setup is needed. Put HTTPS in front (e.g. Caddy or a cloud load balancer). Naming `web` starts only the prod stack; the dev services (`docker compose up`) are separate.
