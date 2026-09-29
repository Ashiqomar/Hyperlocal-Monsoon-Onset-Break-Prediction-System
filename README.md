# Monsoon Decision Twin

Full-stack scaffold for the Monsoon Decision Twin.

| Part      | Stack                                            | Port |
|-----------|--------------------------------------------------|------|
| `backend` | Python 3.11, FastAPI, SQLAlchemy 2               | 8000 |
| `frontend`| React, Vite, TypeScript, Tailwind CSS            | 5173 |
| database  | SQLite for local dev, PostgreSQL 16 in Docker    | 5432 (internal) |

```
monsoon-decision-twin/
├── backend/
│   ├── app/
│   │   ├── api/               # routes: health, forecast, twin, decision, review, notify, feedback
│   │   ├── core/config.py     # settings from env vars
│   │   ├── data/              # synthetic data, crop response + suitability tables
│   │   ├── db/                # engine/session (DB-agnostic), Base, seeding
│   │   ├── models/            # SQLAlchemy models: Block, Panchayat, Feedback
│   │   ├── schemas/           # Pydantic response models
│   │   ├── services/          # forecast ensemble, scenario twin, decision, review store
│   │   └── main.py            # FastAPI app
│   ├── tests/
│   ├── requirements.txt       # runtime deps (requirements-dev.txt adds pytest)
│   └── Dockerfile
├── frontend/
│   ├── src/                   # App.tsx (officer dashboard), pages/ (farmer, feedback admin), api.ts
│   ├── vite.config.ts         # proxies /api -> backend (dev)
│   ├── Dockerfile             # dev server (default compose stack)
│   ├── Dockerfile.prod        # build + nginx (prod profile)
│   ├── nginx/                 # nginx config template for the prod image
│   └── vercel.json            # SPA rewrites for Vercel
├── docker-compose.yml         # dev stack (default) + prod profile
├── render.yaml                # Render blueprint (backend + Postgres)
└── DEPLOY.md
```

## Option 1: Run everything with Docker

Needs Docker Desktop.

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

In Docker the backend uses the bundled Postgres container. Stop with `Ctrl+C`; run `docker compose down -v` to also delete the database volume.

**Production-like stack** (nginx serving the built frontend and proxying `/api`, on :8080): `cp .env.example .env`, then `docker compose --profile prod up -d --build web`.

## Deploying

See **[DEPLOY.md](DEPLOY.md)** for Render/Railway (backend) and Vercel (frontend). Env templates:
- `.env.example`: compose prod profile
- `backend/.env.example`
- `frontend/.env.example`

## Option 2: Run locally without Docker (SQLite)

Needs Python 3.11+ and Node 20.19+ (or 22.12+).

**Backend** (terminal 1):

```bash
cd backend
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps + pytest
uvicorn app.main:app --reload
```

This creates `backend/monsoon.db` (SQLite) on first start.

**Frontend** (terminal 2):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dashboard header should show a green "Backend ok" status (the map tiles need internet access).

**Tests:**

```bash
cd backend
pytest
```

## API

| Endpoint | Returns |
|----------|---------|
| `GET /health` | Service status and DB connectivity |
| `GET /panchayats` | All 30 panchayats with block, district, lat/lon, soil, irrigation, primary crop |
| `GET /forecast/{panchayat_id}` | 4-week probabilistic rainfall forecast (e.g. `/forecast/GP001`) |
| `GET /twin/{panchayat_id}?crop=` | Scenario simulation: probability, yield/cost impact, expected profit and downside risk per rainfall scenario (e.g. `/twin/GP014`) |
| `GET /decisions` | Recommendation, confidence and suitability for every panchayat's primary crop (feeds the dashboard map) |
| `GET /review-queue?status=pending\|reviewed\|all` | Today's decisions flagged for officer review (primary crops), pending first |
| `POST /review-queue/{id}/approve` | Approve a flagged decision (optional `note`) |
| `POST /review-queue/{id}/override` | Replace it with another `action`; `note` (reason) required |
| `GET /notify/{panchayat_id}` | Preview today's WhatsApp-style farmer message (nothing is sent or logged) |
| `POST /notify/{panchayat_id}` | "Send" the message: currently **logged on the server only**; 409 while the decision awaits officer review |
| `POST /feedback` | Record a farmer's outcome: `panchayat_id`, `rain_occurred` (bool), `action_taken` (`sowed`/`waited`/`sprayed`/`nothing`), optional `note` |
| `GET /feedback?limit=&panchayat_id=` | Recent feedback, newest first |
| `GET /decision/{panchayat_id}?crop=` | Expected-loss table for SOW / WAIT / SPRAY / REASSESS, recommended action with confidence, and a separate crop-suitability score |

Full response schemas are at http://localhost:8000/docs.

### Synthetic data

On first start the backend seeds 10 Blocks and 30 Panchayats (`GP001`–`GP030`, 3 per block) from `backend/app/data/synthetic.py`. Block centroids are real talukas covering Maharashtra's agro-climatic zones (Konkan, the Western Maharashtra rain shadow, North Maharashtra, Marathwada, Vidarbha). Panchayat names, coordinates and attributes are fake, generated with a fixed seed, so every database gets identical data.

### Mock forecast

`/forecast/{id}` is **synthetic** (`"synthetic": true` in the response). For each panchayat it runs a 200-member ensemble of daily rainfall over 28 days, driven by the block's climatology. All numbers are read off that ensemble:

- `rainfall_mm.p10/p50/p90`: quantiles of weekly total rainfall
- `dry_spell_probability`: share of members with ≥5 consecutive days < 2.5 mm within the week
- `heavy_rain_probability`: share of members with at least one day ≥ 64.5 mm (IMD "heavy rain")

The random seed comes from the panchayat id, so a panchayat always returns the same numbers. Only the dates move with the issue date (today).

### Scenario twin

`/twin/{id}` classifies each of the same 200 forecast ensemble members into one scenario. Each scenario's probability is the share of members in it, so the probabilities sum to 1 and match `/forecast`:

| Scenario | Rule (over the 4 weeks) |
|----------|------------------------|
| False onset | ≥ 20 mm within 3 days in week 1, then a ≥ 10-day dry spell (checked first) |
| Dry | total < 80% of block normal |
| Wet | total > 120% of block normal |
| Normal | everything else |

Each scenario then applies per-crop coefficients from `backend/app/data/crop_response.py`: a yield factor, an extra cost, and a yield spread. All results are per hectare, in ₹:

- `expected_profit_inr_per_ha`: normal yield × yield factor × price, minus (base cost + extra cost)
- `profit_p10_inr_per_ha`: profit in a 1-in-10 bad outcome within the scenario
- `downside_risk_inr_per_ha`: how far that 1-in-10 outcome falls below a normal season's profit

Coefficients exist for **cotton, soybean and paddy**. The panchayat's primary crop is used by default. For other crops the endpoint returns 422; pass `?crop=cotton|soybean|paddy` to override. The coefficients are illustrative (yields near state averages, prices near the 2025-26 MSP) and need agronomist review before any real use.

### Decision

`/decision/{id}` takes the twin output and, for each action and scenario, sets a **cost if wrong**: the per-hectare loss vs a normal season. **Expected loss** = Σ P(scenario) × cost if wrong. The recommended action is the one with the lowest expected loss.

| Action | Meaning | Cost if wrong |
|--------|---------|---------------|
| SOW | Sow now | The twin's profit shortfall for the scenario (0 in Normal) |
| WAIT | Delay sowing 1–2 weeks | 10% late-sowing yield loss, but avoids all false-onset losses and 40% of dry-season losses |
| SPRAY | Sow + protective spray | SOW's losses + ₹2,500 spray cost; prevents 40% of wet-season losses |
| REASSESS | Hold a week, decide on the next forecast | 4% delay loss; then 70% chance of picking the best action for the actual scenario |

The coefficients are in `backend/app/services/decision.py` and are illustrative.

The response has **two separate scores. They measure different things and should never be combined:**

- `recommendation.confidence` (0–1): how strongly *this forecast* supports the action. It is the share of forecast outcomes in which the action turns out to be the best one to commit to. For REASSESS, it is the share of outcomes in which committing now would be the wrong call.
- `crop_suitability.score` (0–100): the long-term fit of the crop to the panchayat. It is 50% soil fit plus 50% water fit (the block's normal monsoon rainfall vs the crop's range, with irrigation making up part of any shortfall). It never uses the forecast. Tables are in `backend/app/data/crop_suitability.py`.

Example: GP007 (Niphad, soybean) scores 95 for suitability, a very good place for soybean. This week's forecast is split between normal and wet, so the recommendation is REASSESS with confidence 0.53.

### Escalation and officer review

Every `/decision` response has an `escalation` block. A decision is flagged **needs officer review** if either rule fires:

| Rule | Condition (constants in `backend/app/services/decision.py`) |
|------|-------------------------------------------------------------|
| `low_confidence` | Confidence below 0.4, the same cut-off the farmer screen calls "not very sure" |
| `high_impact_cost` | At least a 20% chance of a scenario in which the recommended action loses at least a normal season's whole profit |

`escalation.status` is one of:
- `auto_approved`: not flagged
- `needs_officer_review`: flagged, not yet reviewed
- `approved`: an officer confirmed the recommendation
- `overridden`: an officer chose a different action

`escalation.final_action` is the action to act on: the officer's override if there is one, otherwise the recommendation. The model's own `recommendation` is kept unchanged for audit. `/decisions` (map colours) and the farmer screen both use `final_action`.

The **review queue** is recomputed from today's primary-crop decisions on every request. Only officer actions are stored, keyed by `panchayat:crop:date`, so each day's decision needs its own review. Reviews for a previous day are rejected (409).

⚠ The store is **in memory**: reviews are lost on restart and aren't shared between multiple worker processes. Replace `ReviewStore` in `backend/app/services/review.py` with a database table before production.

### Farmer notifications (WhatsApp, log only)

`/notify/{id}` turns today's decision for the panchayat's **primary crop** into a short WhatsApp-style message:
- the final action in plain English (the officer's override if there is one), with WhatsApp `*bold*`
- this week's rain
- a "checked by your agriculture officer" line if an officer reviewed it
- a link to the farmer screen

Crops without a model get a weather-only message.

- **Not actually sent.** `POST` writes the message to the server log (`[app.notify] WhatsApp message (not sent, log only) …`) and returns `delivery.provider = "log"`. The TODO in `backend/app/services/notify.py` shows how to wire up Twilio's WhatsApp API with `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` and `TWILIO_WHATSAPP_FROM` (already read by `app/core/config.py`; see `.env.example`). Real sending also needs a farmer opt-in/phone list and, for business-initiated messages, a WhatsApp-approved template.
- **Translation placeholder.** Each message includes `translations: [{language: "mr", status: "pending", text: null}]`. Set the language with `NOTIFY_REGIONAL_LANGUAGE`.
- **Review gate.** Decisions awaiting officer review can be previewed but not sent (409) until they are approved or overridden.
- Message links use `PUBLIC_APP_URL` (default `http://localhost:5173`).
- The message wording mirrors the farmer screen's (`frontend/src/lib/farmerCopy.ts`); keep the two in sync.

### Farmer feedback

`POST /feedback` stores a farmer's reported outcome in the database (`feedback` table). With each report it saves a **snapshot of the advice showing at the time**: final action, review status, the model's action and confidence, and the decision date. Decisions are recomputed daily, so without the snapshot we couldn't later tell what the farmer was told. `followed_advice` is worked out on read: WAIT and REASSESS count "waited" or "nothing" as followed.

**Captured for eventual periodic recalibration only.** Nothing feeds back into the forecast, twin or decision models yet (see the notes in `backend/app/api/feedback.py` and `app/models/feedback.py`).

Admin page: http://localhost:5173/admin/feedback, also linked from the dashboard header as "Farmer feedback". It shows:
- a panchayat filter and a "latest N" setting
- summary tiles: rain reported and share who followed the advice
- a table with the time, panchayat, crop, rain yes/no, what the farmer did, the advice shown and whether they followed it

There's no farmer-facing form yet; submit through the API (see the example on the page's empty state). There's no auth, so the list is open to anyone who can reach the API.

## Officer dashboard (frontend)

Open http://localhost:5173.

- **Map** (Leaflet, OpenStreetMap tiles): one marker per panchayat, coloured by the recommended action for its primary crop:
  - green = SOW
  - amber = WAIT
  - red = SPRAY (caution)
  - sky blue = REASSESS
  - hollow grey = crop not modelled yet

  The legend shows how many panchayats have each colour. Hover a marker for a quick summary; click it for full detail.
- **Side panel**, top to bottom:
  - Recommendation with its rationale.
  - **Decision confidence** and **crop suitability**, shown as separate cards on separate scales and never combined.
  - **WhatsApp message**: a chat-bubble preview of the farmer message, with the Marathi translation placeholder, **Send (log only)** (disabled while the decision awaits review) and **Copy text**.
  - Expected-loss table: the cost if wrong for each action × scenario.
  - Twin scenarios: probabilities, yield and cost impact, expected profit, downside risk.
  - 4-week forecast: P10–P90 rainfall range with P50, dry-spell and heavy-rain probabilities.
- **Crop picker:** "Analyse for" re-runs the twin and decision for cotton, soybean or paddy. Panchayats whose primary crop isn't modelled need one picked first. The map colour always uses the primary crop.
- **Review queue** (the default tab when no marker is selected; the badge shows the pending count): each flagged decision shows the model's action, confidence, expected loss and the flag reasons.
  - **Approve** confirms it.
  - **Override…** picks another action and requires a reason.
  - Reviewed items move to "Reviewed today" and can be changed later.
  - After each review the map, list and farmer screen update. Markers awaiting review have a dashed amber outline, and the detail panel shows a banner with the review status and officer note.
- **All panchayats** tab: every panchayat with its action and status; click a row to open it.

Each panchayat's panel has a **Farmer view ↗** link to its farmer screen.

## Farmer screen (`/farmer/{panchayat_id}`)

A mobile-first screen for farmers, e.g. http://localhost:5173/farmer/GP014. It's built to work on a basic 360px-wide phone: large text, tap targets of at least 56px, no sideways scrolling, and it doesn't download the dashboard or map code (~105 KB gzipped).

- A greeting with the village name and today's date.
- **One advice card** with the recommended action in plain words ("Wait before sowing", "Sow, but protect your cotton"), a few concrete steps, and a colour for the action.
- **"Why this advice?"** (tap to expand), in plain language:
  - this week's rain in words, e.g. "light rain, about 24 mm"
  - the biggest worry, as a chance like "5 in 10"
  - the rough saving per acre compared with the next best choice
  - **how sure we are**
  - **how well the land suits the crop**, as a separate point
- **Listen to voice note**: a placeholder only. Play, pause, resume and finish work with a progress bar, but there is no audio yet.
- If the panchayat's crop isn't modelled, it says advice is "coming soon" and shows this week's weather instead. An unknown ID shows "Village not found".

All farmer-facing wording is in `frontend/src/lib/farmerCopy.ts`, ready for review and translation (e.g. Marathi).

Code: `frontend/src/pages/FarmerPage.tsx`, `src/components/farmer/`, `frontend/src/components/` (map, panel sections), `src/types.ts` (TypeScript types mirroring the backend's Pydantic models; keep in sync), `src/api.ts`.

## Database: SQLite vs PostgreSQL

The backend reads a single `DATABASE_URL` env var (see `backend/.env.example`). Everything goes through SQLAlchemy, so switching databases only means changing that URL:

```bash
# SQLite (default)
DATABASE_URL=sqlite:///./monsoon.db

# PostgreSQL
DATABASE_URL=postgresql+psycopg://monsoon:monsoon@localhost:5432/monsoon
```

Copy `backend/.env.example` to `backend/.env` to set it locally. The Postgres driver (`psycopg`) is already in `requirements.txt`. When the schema starts changing, add Alembic migrations in place of the `create_all` call in `app/main.py`.

## How the frontend reaches the backend

The browser calls `/api/...`. The Vite dev server proxies that to `BACKEND_URL` (default `http://localhost:8000`; `http://backend:8000` in Docker) and strips the `/api` prefix. So `/api/health` → `GET /health`. To call the backend directly instead, set `VITE_API_BASE`, e.g. `VITE_API_BASE=http://localhost:8000`. The backend's CORS allowlist (`CORS_ORIGINS`) already includes `http://localhost:5173`.
