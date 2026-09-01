# 🌡️ ThermoShelter

> **Shelter thermal analysis & optimisation platform** — simulate heat flow through building envelopes, then automatically discover the material + geometry combination that best balances energy efficiency, thermal comfort, and construction cost.

---

## Table of Contents

1. [What is ThermoShelter?](#what-is-thermoshelter)
2. [High-Level Architecture](#high-level-architecture)
3. [Repository Layout](#repository-layout)
4. [Tech Stack](#tech-stack)
5. [Current Work — v2 Status](#current-work--v2-status)
6. [Feature Flags](#feature-flags)
7. [Quick Start](#quick-start)
8. [API Overview](#api-overview)
9. [Key Workflows](#key-workflows)
10. [Database Schema](#database-schema)
11. [Scientific Engine Interface](#scientific-engine-interface)
12. [Contributing](#contributing)

---

## What is ThermoShelter?

ThermoShelter helps engineers and architects answer three questions about any shelter design:

| Question | Feature |
|---|---|
| *How will this shelter behave thermally?* | **Transient simulation** — hourly heat-flow, indoor temperature, comfort hours |
| *What is the best material/geometry combo?* | **Multi-objective optimisation** — scores candidates on energy, comfort & cost |
| *Why is this the best design?* | **Explainable recommendation** — data-grounded narrative + comparison report |

---

## High-Level Architecture

```
┌─────────────┐
│   Frontend  │  (React / any HTTP client)
└──────┬──────┘
       │ REST/JSON
┌──────▼─────────────────────────────────────────┐
│              FastAPI  (port 8000)               │
│  • Routes, Pydantic validation, DB persistence  │
│  • Orchestrates jobs, builds reports            │
└──────┬──────────────────────┬───────────────────┘
       │                      │
  sync mode              async mode
(dev default)      (USE_BACKGROUND_JOBS=true)
       │                      │
       │            ┌─────────▼──────────┐
       │            │   Redis + Celery    │
       │            │   Worker Process    │
       │            └─────────┬──────────┘
       │                      │
┌──────▼──────────────────────▼───────────────────┐
│      Scientific Engine  (app/scientific_engine)  │
│  • Thermal physics  (physics/engine.py)          │
│  • Transient solver (transient/solver.py)        │
│  • Optimiser        (optimization/engine.py)     │
└──────────────────────────┬──────────────────────┘
                           │
               ┌───────────▼───────────┐
               │  PostgreSQL Database   │
               │  (results, history)    │
               └───────────────────────┘
```

### Layer Responsibilities

| Layer | Owns |
|---|---|
| **FastAPI** | Routes, validation, persistence, orchestration, report assembly |
| **Scientific Engine** | Thermal physics, transient simulation, optimisation algorithms |
| **Celery Workers** | Background task execution, status & error updates |
| **PostgreSQL** | All persistent state — projects, runs, results, candidates |

---

## Repository Layout

```
ThermoShelter/
└── backend/                        ← Python / FastAPI backend (currently active)
    ├── app/
    │   ├── main.py                 # FastAPI entry point + lifespan hooks
    │   ├── core/
    │   │   ├── config.py           # Settings + feature flags (from .env)
    │   │   └── constants.py        # Enums, RunStatus, physics defaults
    │   ├── database/
    │   │   ├── base.py             # SQLAlchemy declarative base
    │   │   ├── session.py          # Engine + SessionLocal factory
    │   │   └── init_db.py          # Seed: materials library, climate presets
    │   ├── models/                 # SQLAlchemy ORM models
    │   │   ├── project.py
    │   │   ├── climate.py          # ClimateProfile (incl. hourly time-series JSON)
    │   │   ├── shelter.py          # Shelter geometry & envelope
    │   │   ├── material.py         # Thermal material catalogue
    │   │   ├── simulation.py       # SimulationRun + SimulationResult
    │   │   └── optimization.py     # OptimizationRun + OptimizationCandidate
    │   ├── schemas/
    │   │   ├── contracts.py        ← GLOBAL DATA CONTRACTS (single source of truth)
    │   │   ├── report.py           # Report + recommendation schemas
    │   │   └── *.py                # Per-entity request/response schemas
    │   ├── routers/                # FastAPI route handlers (one file per domain)
    │   ├── services/
    │   │   ├── project_service.py       # DB → typed request assembly
    │   │   ├── validation_service.py    # Pre-flight engineering checks
    │   │   ├── comparison_service.py    # Baseline vs optimised delta
    │   │   ├── recommendation_service.py# Explainable design recommendation
    │   │   ├── report_service.py        # Full project report assembly
    │   │   ├── simulation_service.py    # (legacy compat wrapper)
    │   │   └── optimization_service.py  # (legacy compat wrapper)
    │   ├── workers/
    │   │   ├── celery_app.py            # Celery configuration + broker setup
    │   │   ├── simulation_tasks.py      # Async simulation Celery task
    │   │   └── optimization_tasks.py    # Async optimisation Celery task
    │   └── scientific_engine/      ← Physics team owns this package
    │       ├── contracts.py        # Re-exports from schemas/contracts.py (decoupled)
    │       ├── physics/engine.py   # run_transient_simulation() — mock + stub
    │       ├── transient/solver.py # Time-series transient wrapper
    │       └── optimization/engine.py # run_optimization() — mock + stub
    ├── alembic/
    │   └── versions/
    │       ├── 001_initial_schema.py   # 8-table initial schema
    │       └── 002_v2_architecture.py  # v2 columns: task_id, comfort metrics, JSONB
    ├── docker-compose.yml          # PostgreSQL + Redis + FastAPI + Celery
    ├── requirements.txt
    ├── .env.example
    └── README.md                   # Backend-specific deep-dive documentation
```

> **Note:** A frontend (React/Next.js) is not yet in the repo. The API is designed to be frontend-agnostic and pre-configured for CORS on `localhost:3000` and `:5173`.

---

## Tech Stack

| Category | Technology |
|---|---|
| **API Framework** | [FastAPI](https://fastapi.tiangolo.com/) 0.111 + Uvicorn |
| **ORM / Migrations** | SQLAlchemy 2.0 + Alembic |
| **Database** | PostgreSQL (JSONB for time-series & config blobs) |
| **Task Queue** | Celery 5.3 + Redis |
| **Data Validation** | Pydantic v2 |
| **Scientific Computing** | NumPy 1.26, SciPy 1.13 |
| **Report Generation** | ReportLab 4.2 (PDF, WIP) |
| **Containerisation** | Docker + Docker Compose |

---

## Current Work — v2 Status

### ✅ Completed

| Area | Detail |
|---|---|
| **Project CRUD** | Full create / read / update / delete for projects |
| **Climate profiles** | Custom + preset modes; optional hourly time-series JSON stored in `ClimateProfile.time_series_data` |
| **Shelter config** | Geometry, envelope, material references |
| **Materials catalogue** | Seeded library with thermal properties; filterable by category |
| **Simulation pipeline** | `POST /simulate` → `SimulationRun` → sync or async execution → result persisted |
| **Optimisation pipeline** | `POST /optimize` → `OptimizationRun` → candidates scored → winner flagged |
| **Celery background jobs** | `simulation_tasks.py` + `optimization_tasks.py` with retry logic; toggled by `USE_BACKGROUND_JOBS` |
| **Data contracts** | `app/schemas/contracts.py` is the single source of truth consumed by all layers |
| **Scientific engine decoupling** | `scientific_engine/contracts.py` re-exports contracts so physics code never imports FastAPI |
| **Validation service** | Pre-flight engineering checks before any run is created |
| **Comparison service** | Baseline vs optimised energy / comfort / cost delta |
| **Recommendation service** | Data-grounded, explainable design narrative from actual scores |
| **Report service** | Full structured JSON report assembled from all sub-services |
| **Database migrations** | `001` (8-table initial schema) + `002` (v2: `task_id`, comfort metrics, JSONB blobs) |
| **Feature flag system** | `USE_BACKGROUND_JOBS`, `USE_MOCK_SIMULATION`, `USE_MOCK_OPTIMIZATION` — zero code changes needed |
| **Docker Compose stack** | One-command full-stack startup |
| **Health endpoint** | `GET /health` reports live flag state for ops visibility |

### 🚧 In Progress / Planned

| Area | Status | Notes |
|---|---|---|
| **Real physics engine** | 🔧 Stub exists | `physics/engine.py` has mock; real transient solver to be implemented by physics team |
| **Real optimiser** | 🔧 Stub exists | `optimization/engine.py` has mock; multi-objective search (e.g. NSGA-II) pending |
| **PDF report** | 🔧 501 stub | `GET /report/pdf` returns 501; ReportLab integrated but generation not wired |
| **Transient replay** | 📋 Planned | Hourly climate time-series stored; `transient/solver.py` to consume it |
| **Frontend** | 📋 Planned | React or Next.js UI; CORS pre-configured |
| **Authentication** | 📋 Planned | No auth layer yet; API is open |
| **Rate limiting** | 📋 Planned | No rate limiting on compute-heavy endpoints |
| **Production deployment** | 📋 Planned | CI/CD, secrets management, environment hardening |

---

## Feature Flags

All flags are set in `.env` — no code changes required:

| Flag | Default | Effect |
|---|---|---|
| `USE_BACKGROUND_JOBS` | `false` | `true` → async via Celery+Redis; `false` → synchronous (no Redis needed) |
| `USE_MOCK_SIMULATION` | `true` | `true` → mock physics results; `false` → real engine |
| `USE_MOCK_OPTIMIZATION` | `true` | `true` → mock optimiser; `false` → real engine |

> 💡 **For local development** keep `USE_BACKGROUND_JOBS=false`. The entire API works without Redis or Celery installed.

---

## Quick Start

### Option A — Local (no Docker)

```bash
# 1. Clone
git clone <repo-url>
cd ThermoShelter/backend

# 2. Virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL to your PostgreSQL connection string

# 5. Run migrations
alembic upgrade head

# 6. Start the API
uvicorn app.main:app --reload
# → Swagger UI: http://localhost:8000/docs
# → ReDoc:      http://localhost:8000/redoc
```

### Option B — Docker Compose (full stack)

```bash
cd ThermoShelter/backend
docker-compose up --build
# Starts: PostgreSQL + Redis + FastAPI + Celery worker
# → http://localhost:8000/docs
```

### Running the Celery Worker (standalone)

Only needed when `USE_BACKGROUND_JOBS=true`:

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — Celery worker
cd backend && source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3 — FastAPI
uvicorn app.main:app --reload
```

---

## API Overview

Full interactive docs at **`/docs`** (Swagger) and **`/redoc`**.

| Group | Endpoints |
|---|---|
| **Health** | `GET /health` |
| **Projects** | `POST /api/projects` · `GET /api/projects` · `GET\|PUT\|DELETE /api/projects/{id}` |
| **Climate** | `POST\|GET\|PUT /api/projects/{id}/climate` · `GET /api/climate-presets` |
| **Shelter** | `POST\|GET\|PUT /api/projects/{id}/shelter` |
| **Materials** | `GET\|POST /api/materials` · `GET\|PUT /api/materials/{id}` |
| **Simulation** | `POST /api/projects/{id}/simulate` · `GET /api/simulations/{run_id}/status` · `GET /api/simulations/{run_id}/result` |
| **Optimisation** | `POST /api/projects/{id}/optimize` · `GET /api/optimization/{run_id}/status` · `GET /api/optimization/{run_id}/result` |
| **Analysis & Reports** | `GET /api/projects/{id}/validate` · `/comparison` · `/recommendation` · `/report` · `/report/pdf` *(501)* |

---

## Key Workflows

### Simulation

```
POST /api/projects/{id}/simulate
  → validate project (climate + shelter + materials present)
  → create SimulationRun  (status=pending)
  → USE_BACKGROUND_JOBS=false: run physics engine synchronously
    USE_BACKGROUND_JOBS=true:  queue Celery task → worker picks up
  → save SimulationResult (time-series JSONB, energy totals, comfort metrics)
  → poll: GET /api/simulations/{run_id}/status
  → fetch: GET /api/simulations/{run_id}/result
```

### Optimisation

```
POST /api/projects/{id}/optimize
  → validate project
  → create OptimizationRun  (status=pending)
  → run optimisation engine (sync or via Celery)
  → generate N candidates → score each (energy / comfort / cost)
  → flag winner → persist candidates + comparison_data + baseline_data JSON
  → GET /api/optimization/{run_id}/result
  → GET /api/projects/{id}/comparison      ← baseline vs optimised delta
  → GET /api/projects/{id}/recommendation  ← explainable narrative
  → GET /api/projects/{id}/report          ← full structured report
```

---

## Database Schema

8 tables across 2 Alembic migrations:

```
projects
  ├── climate_profiles      (1:1, CASCADE delete)
  ├── shelters              (1:1, CASCADE delete)
  ├── simulation_runs       (1:N)
  │     └── simulation_results      (1:1 per run — JSONB time-series)
  └── optimization_runs     (1:N)
        └── optimization_candidates (1:N per run — one flagged is_winner)

materials                   (standalone catalogue, referenced by shelters)
```

**Key JSONB columns:**

| Column | Purpose |
|---|---|
| `simulation_results.time_series_data` | Hourly heat-flow snapshots |
| `climate_profiles.time_series_data` | Optional hourly climate replay data |
| `optimization_runs.comparison_data` | Delta metrics vs baseline |
| `optimization_runs.baseline_data` | Baseline simulation snapshot |
| `optimization_candidates.config` | Full material + geometry config blob |

---

## Scientific Engine Interface

The physics team implements exactly **two functions** inside `app/scientific_engine/`:

```python
# app/scientific_engine/physics/engine.py
def run_transient_simulation(request: SimulationRequest) -> SimulationResult:
    """Given climate + shelter inputs, return thermal simulation results."""
    ...

# app/scientific_engine/optimization/engine.py
def run_optimization(request: OptimizationRequest) -> OptimizationResult:
    """Given project constraints, return ranked design candidates + winner."""
    ...
```

**Rules for scientific engine code:**
- Import **only** from `app/scientific_engine/contracts.py` — never from `app.schemas` or FastAPI directly
- All data contracts are defined in `app/schemas/contracts.py` and re-exported cleanly
- Toggle real engines on with `USE_MOCK_SIMULATION=false` / `USE_MOCK_OPTIMIZATION=false`

---

## Contributing

| Directory | Team |
|---|---|
| `backend/app/scientific_engine/` | Physics / simulation team |
| `backend/app/routers/` | API / backend team |
| `backend/app/services/` | API / backend team |
| `backend/app/models/` | Backend team (DB changes require an Alembic migration) |

**Ground rules:**
1. Never import `fastapi` or `sqlalchemy` inside `scientific_engine/`
2. All new DB columns must have a corresponding Alembic migration file
3. Use feature flags to ship incomplete features safely
4. Run `alembic upgrade head` after pulling any migration changes

---

*ThermoShelter v2 — FastAPI · PostgreSQL · Celery · Redis · NumPy · SciPy*
