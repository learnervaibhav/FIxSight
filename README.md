# FixSight: Agentic Predictive Maintenance

FixSight watches vehicle OBD-II telemetry, predicts faults before they happen, explains them with an LLM, books the nearest service center, and texts the owner. A live simulation drives the whole loop so you can watch it on a dashboard and a map.

```
telemetry → XGBoost fault classifier → XGBoost RUL forecast → Gemini explanation
          → maintenance plan → [needs service?] book nearest open center → [severe?] SMS (Twilio or mock)
```

Stack: **FastAPI · SQLAlchemy 2 · PostgreSQL · Alembic · LangGraph · XGBoost · Gemini · Twilio · React 19 · Vite · Tailwind 4 · Leaflet**

---

## Run with Docker (recommended)

Requirements: Docker Desktop and [Git LFS](https://git-lfs.com) (bundled with Git for Windows). The trained models in `ml_models/` and the dataset in `dataset/` are stored with Git LFS.

```bash
git lfs install                     # once per machine
git clone https://github.com/learnervaibhav/FIxSight.git && cd FIxSight
git lfs pull                        # only if the clone happened before LFS was installed
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8080 | Dashboard |
| http://localhost:8000/docs | API (Swagger) |
| `localhost:5434` | Postgres (`fixsight` / `fixsight`), change with `FIXSIGHT_DB_PORT` |

On first start the backend container waits for Postgres, runs migrations, trains models if `ml_models/` is missing (a few minutes), and seeds 10 owners, 15 vehicles, 10 Delhi NCR service centers and 24 h of telemetry. Data persists in the `pgdata` volume. `docker compose down -v` wipes it.

**Secrets (optional).** Compose reads `app/core/.env` if present (template: `.env.example`):

- `GOOGLE_API_KEY`: Gemini explanations. Without it, rule-based explanations are used.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `ALERT_SMS_TO` and a sender (`TWILIO_FROM_NUMBER` = a number owned by the account, or `TWILIO_MESSAGING_SERVICE_SID` with at least one number): needed only for **Simulation – Real**. Opening the Simulation dropdown runs a read-only Twilio check (`GET /api/simulation/twilio-check`) and lists anything that would make SMS fail; failures during a run show Twilio's error code on the dashboard.
- `SIM_REAL_SMS_LIMIT` (default 10): caps real SMS per simulation run.

## Using the simulation

Click **Simulation ▾** in the top bar:

- **Simulation – Real**: sends real SMS through Twilio (asks for a second click to confirm; disabled if Twilio isn't configured).
- **Simulation – Mock**: no SMS; every alert pops up as an in-app *DEV · Mock SMS* notification and is logged.

The dropdown also has speed (Fast/Normal/Slow), **Step one tick**, and **Reset** (stops the run and cancels open bookings).

Each tick advances a simulated clock (20 min) and sends a reading for the next 5 vehicles; a **round** completes when all vehicles have reported. Some vehicles develop faults (coolant overheating, low oil pressure, battery drop, transmission overheat, MAF sensor). When the classifier catches one:

1. A fault prediction and RUL forecast are stored; Gemini explains it (once per episode).
2. The nearest service center with free bays (10 km radius first) is booked at its next opening.
3. The owner is alerted (real or mock SMS).
4. At the booked time the vehicle checks in (*in service*), and when the service ends it is repaired, the bay frees up, and a completion SMS is sent.

The map, occupancy bars, fleet table and activity feed update live.

## Run locally (development)

Requirements: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node 20.19+ / 22, PostgreSQL.

```bash
# 1. Database (once)
psql -U postgres -c "CREATE USER fixsight_user WITH PASSWORD 'password';"
psql -U postgres -c "CREATE DATABASE fixsight_db OWNER fixsight_user;"
cp .env.example app/core/.env        # then edit DATABASE_URL / keys

# 2. Backend
uv sync
uv run alembic upgrade head
uv run python scripts/bootstrap.py   # idempotent demo data
uv run uvicorn app.main:app --reload # http://localhost:8000

# 3. Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api to :8000)
```

Optional, using the full synthetic dataset (≈250 MB CSV, ~1M rows):

```bash
uv run python scripts/generate_dataset.py              # dataset/*.csv
uv run python scripts/seed_database.py --truncate      # load CSVs into Postgres
uv run python scripts/train_model.py --out ml_models   # retrain models
```

Tests (isolated SQLite, no external services):

```bash
uv run pytest
```

## API overview

| Endpoint | Purpose |
|---|---|
| `GET /api/fleet/overview` | Per-vehicle health, latest prediction, RUL, service state + fleet summary |
| `POST /api/agent/run/{vehicle_id}` | Run the agent graph on `telemetry_row` or `telemetry_reading_id` |
| `GET /api/vehicles/{id}/telemetry`, `/predictions` | History for charts |
| `GET /api/predictions/faults` | Fleet-wide fault predictions with explanations |
| `GET /api/service/centers`, `/centers/nearby`, `/centers/{id}/occupancy` | Service network |
| `POST /api/service/schedule`, `GET /api/service/slots`, `PATCH /api/service/slots/{id}` | Bookings |
| `GET /api/alerts` | SMS / notification log |
| `POST /api/simulation/start|stop|reset|tick`, `GET /api/simulation/status` | Simulation control |
| `GET /api/events?after_id=` | Live event feed (polled by the dashboard) |

## Project layout

```
app/
  agents/      LangGraph state, graph and nodes (ingest, diagnose, RUL, LLM, advise, schedule, alert)
  api/routers/ vehicles, telemetry, agent, service, fleet, simulation
  core/        config (.env in app/core), database, in-process event bus
  ml/          model loading + inference (fault classifier, RUL regressor)
  models/      SQLAlchemy ORM          schemas/   Pydantic API contracts
  services/    business logic (fleet, scheduling, notifications, ML, agent)
  simulation/  telemetry generator + simulation engine
alembic/       migrations              scripts/   bootstrap, dataset, seeding, training
frontend/      React dashboard         docker/    container entrypoint
ml_models/     trained models (Git LFS)
dataset/       synthetic telemetry CSVs (Git LFS)
```

## Known limitations

- The shipped classifier cannot detect *fuel-trim drift*, *EGR stuck open*, *fuel injector* or *misfire* faults: the dataset generator never produces readings past those rule thresholds, so those classes exist only as label noise. Fixing `scripts/generate_dataset.py` and retraining would enable them.
- Simulation state lives in the API process: restarting the backend stops a running simulation (bookings in the DB are kept).

## License

MIT
