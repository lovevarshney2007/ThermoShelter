# ThermoShelter Backend — v2

A shelter thermal analysis and optimisation platform built with **FastAPI + PostgreSQL + Celery + Redis**.

---

## Architecture

```
Frontend
    ↓
FastAPI API Layer (orchestration, validation, persistence)
    ↓
Background Job Layer (Celery + Redis)
    ↓
Scientific Engine (thermal physics, transient simulation, optimization)
    ↓
PostgreSQL (results, history, traceability)
    ↓
FastAPI → Frontend
```

### Responsibility Boundaries

| Layer | Owns |
|-------|------|
| **FastAPI** | API routes, Pydantic validation, DB persistence, job creation, orchestration |
| **Scientific Engine** (`app/scientific_engine/`) | Thermal physics, transient simulation, optimization algorithms |
| **Celery Workers** (`app/workers/`) | Background task execution, status updates |
| **PostgreSQL** | Project data, simulation history, optimization results |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                         # FastAPI entry point
│   ├── core/
│   │   ├── config.py                   # Settings + feature flags
│   │   └── constants.py                # Enums, status types, physics defaults
│   ├── database/
│   │   ├── base.py / session.py        # SQLAlchemy setup
│   │   └── init_db.py                  # Seed data (materials, presets)
│   ├── models/                         # SQLAlchemy ORM models
│   │   ├── project.py / climate.py / shelter.py / material.py
│   │   ├── simulation.py               # SimulationRun + SimulationResult
│   │   └── optimization.py             # OptimizationRun + OptimizationCandidate
│   ├── schemas/
│   │   ├── contracts.py                ← GLOBAL DATA CONTRACTS (source of truth)
│   │   ├── report.py                   # Report schema
│   │   └── ...                         # Per-entity schemas
│   ├── routers/                        # FastAPI route handlers
│   ├── services/
│   │   ├── project_service.py          # DB → typed request assembly
│   │   ├── validation_service.py       # Pre-flight engineering validation
│   │   ├── comparison_service.py       # Baseline vs optimized comparison
│   │   ├── recommendation_service.py   # Explainability / reasoning
│   │   ├── simulation_service.py       # (legacy, kept for compatibility)
│   │   ├── optimization_service.py     # (legacy, kept for compatibility)
│   │   └── report_service.py           # Full project report assembly
│   ├── workers/
│   │   ├── celery_app.py               # Celery configuration
│   │   ├── simulation_tasks.py         # Celery simulation task
│   │   └── optimization_tasks.py       # Celery optimization task
│   └── scientific_engine/              ← SCIENTIFIC TEAM OWNS THIS
│       ├── contracts.py                # Re-exports from schemas/contracts.py
│       ├── physics/engine.py           # Thermal simulation engine (mock + stub)
│       ├── transient/solver.py         # Time-series transient wrapper
│       └── optimization/engine.py      # Optimization engine (mock + stub)
├── alembic/versions/
│   ├── 001_initial_schema.py           # Initial 8 tables
│   └── 002_v2_architecture.py          # v2 columns (task_id, comfort metrics, etc.)
├── docker-compose.yml                  # Postgres + Redis + FastAPI + Celery
├── requirements.txt
└── .env.example
```

---

## Feature Flags

Controlled via `.env` — no code changes needed:

| Flag | Default | Description |
|------|---------|-------------|
| `USE_BACKGROUND_JOBS` | `false` | `true` = async via Celery; `false` = synchronous fallback |
| `USE_MOCK_SIMULATION` | `true` | `true` = mock physics; `false` = real engine |
| `USE_MOCK_OPTIMIZATION` | `true` | `true` = mock optimizer; `false` = real engine |

> **For development without Redis:** Keep `USE_BACKGROUND_JOBS=false`. Everything runs synchronously.

---

## How to Run

### Option A — Local (no Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure database
cp .env.example .env
# Edit .env: set DATABASE_URL to your PostgreSQL instance

# Apply migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

### Option B — Docker Compose (full stack)

```bash
cd backend
docker-compose up --build
# → API:    http://localhost:8000/docs
# → Swagger: http://localhost:8000/redoc
```

Docker starts: PostgreSQL + Redis + FastAPI + Celery worker.

---

## How to Run the Celery Worker (standalone)

When `USE_BACKGROUND_JOBS=true`:

```bash
# Terminal 1 — Redis (or use docker-compose redis service)
redis-server

# Terminal 2 — Celery worker
cd backend
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3 — FastAPI
uvicorn app.main:app --reload
```

---

## API Reference

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness probe + feature flag status |
| GET | `/docs` | Swagger UI |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects` | Create project |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/{id}` | Get project detail |
| PUT | `/api/projects/{id}` | Update project |
| DELETE | `/api/projects/{id}` | Delete project |

### Climate
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/{id}/climate` | Create/update climate profile |
| GET | `/api/projects/{id}/climate` | Get climate profile |
| PUT | `/api/projects/{id}/climate` | Update climate profile |
| GET | `/api/climate-presets` | List preset climate profiles |

### Shelter
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/{id}/shelter` | Create/update shelter config |
| GET | `/api/projects/{id}/shelter` | Get shelter config |
| PUT | `/api/projects/{id}/shelter` | Update shelter config |

### Materials
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/materials` | List materials (filter: `?category=wall`) |
| POST | `/api/materials` | Create material |
| GET | `/api/materials/{id}` | Get material |
| PUT | `/api/materials/{id}` | Update material |

### Simulation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/{id}/simulate` | Start simulation → returns `{run_id, status}` |
| GET | `/api/projects/{id}/simulations` | List all simulation runs |
| GET | `/api/simulations/{run_id}/status` | **Poll status + progress** |
| GET | `/api/simulations/{run_id}/result` | Get full result (when completed) |
| GET | `/api/simulations/{run_id}` | Get run + result (backward-compat) |

### Optimization
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/{id}/optimize` | Start optimization → returns `{run_id, status}` |
| GET | `/api/optimization/{run_id}/status` | Poll status + progress |
| GET | `/api/optimization/{run_id}/result` | Get candidates + winner |

### Analysis & Report
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/{id}/validate` | Pre-flight validation |
| GET | `/api/projects/{id}/comparison` | Baseline vs optimized delta |
| GET | `/api/projects/{id}/recommendation` | Explainable design recommendation |
| GET | `/api/projects/{id}/report` | Full structured JSON report |
| GET | `/api/projects/{id}/report/pdf` | PDF report (501 — not yet implemented) |

---

## Simulation Flow

```
POST /api/projects/{id}/simulate
        ↓
  Validate project (climate + shelter + materials)
        ↓
  Create SimulationRun (status=pending)
        ↓
  USE_BACKGROUND_JOBS=true? ──→ Queue Celery task ──→ status=queued
                     ↓
                  Redis
                     ↓
                  Worker
                     ↓
        Scientific Engine (physics/engine.py)
                     ↓
          Save SimulationResult → status=completed
        
  USE_BACKGROUND_JOBS=false?
        ↓
  Run synchronously → status=completed immediately
        ↓
  Return 202 {run_id, status, poll_url}
        ↓
  Frontend polls GET /api/simulations/{run_id}/status
        ↓
  GET /api/simulations/{run_id}/result  (when completed)
```

---

## Optimization Flow

```
POST /api/projects/{id}/optimize
        ↓
  Validate project
        ↓
  Create OptimizationRun (status=pending)
        ↓
  Queue / run Optimization Engine
        ↓
  Generate candidates → Score → Select winner
        ↓
  Save candidates + comparison_data + baseline_data
        ↓
  GET /api/optimization/{run_id}/result
        ↓
  GET /api/projects/{id}/comparison
        ↓
  GET /api/projects/{id}/recommendation
        ↓
  GET /api/projects/{id}/report
```

---

## Global Data Contracts

All layers use `app/schemas/contracts.py` as the single source of truth:

- `SimulationRequest` / `SimulationResult`
- `OptimizationRequest` / `OptimizationResult`
- `ClimateInput` / `ShelterInput` / `MaterialInput`
- `ValidationResult`
- `ComparisonResult`
- `JobAcceptedResponse` / `JobStatus`

The scientific engine only imports from `app/scientific_engine/contracts.py`
(which re-exports from the above) — keeping it decoupled from FastAPI.

---

## Scientific Engine Interface

The physics team implements two functions in `app/scientific_engine/`:

```python
# physics/engine.py
def run_transient_simulation(request: SimulationRequest) -> SimulationResult:
    ...

# optimization/engine.py  
def run_optimization(request: OptimizationRequest) -> OptimizationResult:
    ...
```

Set `USE_MOCK_SIMULATION=false` / `USE_MOCK_OPTIMIZATION=false` to activate.

---

## Database Schema

8 tables:
- `projects`, `climate_profiles`, `shelters`, `materials`
- `simulation_runs` (status, task_id, execution_mode)
- `simulation_results` (time-series JSONB, energy totals, comfort metrics)
- `optimization_runs` (comparison_data, baseline_data JSONB)
- `optimization_candidates` (config JSONB, scores, winner flag)
