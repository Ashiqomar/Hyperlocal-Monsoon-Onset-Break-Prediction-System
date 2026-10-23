# Deploying Monsoon Decision Twin

**Backend** (FastAPI + Postgres) on **Render** or **Railway**; **frontend** (static Vite build) on **Vercel**.
The app uses synthetic data, so a fresh deploy seeds 10 blocks and 30 panchayats automatically on first start.

## Before you start (limits to know)

- **Officer reviews live in memory.** They're lost on restart or redeploy (free Render instances also sleep and restart), and aren't shared between instances. Keep **one instance, one worker** (the configs below do). Move the review store to Postgres before real use.
- **Use Postgres, not SQLite**, in the cloud: the container disk is wiped on redeploy. Farmer feedback is stored in the database.
- **No authentication yet.** Anyone with the URLs can use the officer dashboard, review queue and feedback admin page. Don't share them publicly.
- WhatsApp sending is **log only** (see `backend/app/services/notify.py`).

## 1. Deploying on Render

You can deploy the entire stack (Backend + Database + Frontend) directly on Render.

### Option A: Render Blueprint (Recommended — 1-Click)

1. Make sure your latest changes are pushed to GitHub:
   ```bash
   git add .
   git commit -m "Configure Render blueprint and CORS"
   git push origin main
   ```
2. Go to the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Connect and select your GitHub repository (`Hyperlocal-Monsoon-Onset-Break-Prediction-System`).
5. Render will automatically read `render.yaml` and discover:
   - **`monsoon-backend`** (Python Web Service)
   - **`monsoon-frontend`** (Static Site with SPA rewrite rules)
   - **`monsoon-db`** (PostgreSQL Database)
6. Click **Apply**.
7. Once deployed, find your backend URL (e.g. `https://monsoon-backend.onrender.com`):
   - In your Render dashboard, navigate to **`monsoon-frontend`** → **Environment**.
   - Set `VITE_API_BASE` = `https://monsoon-backend.onrender.com` (use your actual backend URL, no trailing slash).
   - Click **Save Changes** and trigger a **Manual Deploy → Deploy latest commit** on `monsoon-frontend` (Vite requires build-time variables).
   - In **`monsoon-backend`** → **Environment**, set `PUBLIC_APP_URL` to your frontend URL (e.g. `https://monsoon-frontend.onrender.com`).

*Note on CORS:* The backend already allows all `https://.*\.onrender\.com` domains by default via `CORS_ORIGIN_REGEX`, so communication works immediately!

---

### Option B: Manual Setup on Render (Step-by-Step)

If you prefer setting up each component manually on Render instead of using the blueprint:

#### Step 1: Create PostgreSQL Database
1. In Render Dashboard, click **New +** → **PostgreSQL**.
2. Name: `monsoon-db`, Region: choose closest to you, Plan: **Free**.
3. Click **Create Database**.
4. Copy the **Internal Database URL** (or External Database URL).

#### Step 2: Deploy Backend Web Service
1. Click **New +** → **Web Service**.
2. Select your repository.
3. Configure the settings:
   - **Name:** `monsoon-backend`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips='*'`
   - **Plan:** Free
4. Under **Advanced** → **Health Check Path**, enter `/health`.
5. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `DATABASE_URL`: paste your database connection string
   - `CORS_ORIGIN_REGEX`: `https://.*(\.onrender\.com|\.vercel\.app)`
6. Click **Deploy Web Service**.
7. Once live, test `https://<your-backend-url>/health`. It should return status `"ok"`.

#### Step 3: Deploy Frontend Static Site
1. Click **New +** → **Static Site**.
2. Select your repository.
3. Configure settings:
   - **Name:** `monsoon-frontend`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
4. Under **Environment Variables**, add:
   - `VITE_API_BASE`: `https://<your-backend-url>` (no trailing slash)
5. Under **Redirects/Rewrites**:
   - Source: `/*`
   - Destination: `/index.html`
   - Action: `Rewrite`
6. Click **Create Static Site**.

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
