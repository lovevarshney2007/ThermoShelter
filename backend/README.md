# ThermoShelter Backend

A thermal analysis and optimisation platform for shelters and buildings.

Built with **FastAPI**, **PostgreSQL**, **SQLAlchemy**, and **Alembic**.

---

## Tech Stack

| Component   | Technology          |
|-------------|---------------------|
| Framework   | FastAPI             |
| Language    | Python 3.11+        |
| Database    | PostgreSQL          |
| ORM         | SQLAlchemy 2.0      |
| Validation  | Pydantic v2         |
| Migrations  | Alembic             |
| Server      | Uvicorn             |
| Config      | pydantic-settings   |

---

## Project Structure

```text
backend/
├── app/
│   ├── main.py              ← FastAPI app factory & router registration
│   ├── core/
│   │   └── config.py        ← Settings from .env
│   ├── database/
│   │   ├── base.py          ← SQLAlchemy DeclarativeBase
│   │   ├── session.py       ← Engine, SessionLocal, get_db dependency
│   │   └── init_db.py       ← Seed data (materials + climate presets)
│   ├── models/              ← SQLAlchemy ORM models
│   ├── schemas/             ← Pydantic request/response schemas
│   ├── routers/             ← FastAPI route handlers
│   ├── services/            ← Business logic (simulation, optimisation, report)
│   └── utils/               ← Shared helpers
├── alembic/                 ← Database migrations
├── requirements.txt
├── .env.example
├── alembic.ini
└── README.md
```

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd ThermoShelter/backend
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
# OR
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Setup

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/thermoshelter
APP_NAME=ThermoShelter API
DEBUG=true
FRONTEND_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## PostgreSQL Setup

### Create the database

```bash
psql -U postgres
CREATE DATABASE thermoshelter;
CREATE USER thermoshelter_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE thermoshelter TO thermoshelter_user;
\q
```

Then update your `.env`:

```env
DATABASE_URL=postgresql://thermoshelter_user:yourpassword@localhost:5432/thermoshelter
```

---

## Database Migrations

### Run existing migrations

```bash
alembic upgrade head
```

### Generate a new migration after model changes

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

### Rollback one migration

```bash
alembic downgrade -1
```

> **Note:** On first startup the application automatically seeds default
> materials (Concrete, Brick, Wood, Rock Wool, etc.) if the table is empty.

---

## Running the Server

```bash
uvicorn app.main:app --reload
```

The server starts at: **http://localhost:8000**

---

## API Documentation

Once the server is running:

- **Swagger UI** → http://localhost:8000/docs
- **ReDoc**       → http://localhost:8000/redoc

---

## API Overview

### Health

| Method | Endpoint  | Description    |
|--------|-----------|----------------|
| GET    | /health   | Liveness probe |

### Projects

| Method | Endpoint                        | Description          |
|--------|---------------------------------|----------------------|
| POST   | /api/projects                   | Create project       |
| GET    | /api/projects                   | List all projects    |
| GET    | /api/projects/{id}              | Get single project   |
| PUT    | /api/projects/{id}              | Update project       |
| DELETE | /api/projects/{id}              | Delete project       |

### Climate

| Method | Endpoint                              | Description              |
|--------|---------------------------------------|--------------------------|
| GET    | /api/climate-presets                  | Get climate presets      |
| POST   | /api/projects/{id}/climate            | Create/upsert climate    |
| GET    | /api/projects/{id}/climate            | Get climate profile      |
| PUT    | /api/projects/{id}/climate            | Update climate profile   |

### Shelter

| Method | Endpoint                              | Description              |
|--------|---------------------------------------|--------------------------|
| POST   | /api/projects/{id}/shelter            | Create/upsert shelter    |
| GET    | /api/projects/{id}/shelter            | Get shelter config       |
| PUT    | /api/projects/{id}/shelter            | Update shelter config    |

### Materials

| Method | Endpoint                    | Description                        |
|--------|-----------------------------|------------------------------------|
| GET    | /api/materials              | List materials (filter by category)|
| GET    | /api/materials/{id}         | Get single material                |
| POST   | /api/materials              | Create material                    |
| PUT    | /api/materials/{id}         | Update material                    |

### Simulation

| Method | Endpoint                                  | Description              |
|--------|-------------------------------------------|--------------------------|
| POST   | /api/projects/{id}/simulate               | Run simulation           |
| GET    | /api/projects/{id}/simulations            | List simulation runs     |
| GET    | /api/simulations/{run_id}                 | Get simulation + result  |

### Optimization

| Method | Endpoint                                  | Description              |
|--------|-------------------------------------------|--------------------------|
| POST   | /api/projects/{id}/optimize               | Run optimisation         |

### Reports

| Method | Endpoint                        | Description              |
|--------|---------------------------------|--------------------------|
| GET    | /api/projects/{id}/report       | Full project report      |

---

## Critical Success Flow

```
POST /api/projects                    → Create project
POST /api/projects/{id}/climate       → Configure climate
POST /api/projects/{id}/shelter       → Configure shelter (with material IDs)
GET  /api/materials                   → Browse/select materials
POST /api/projects/{id}/simulate      → Run thermal simulation
GET  /api/simulations/{run_id}        → View simulation results
POST /api/projects/{id}/optimize      → Run optimisation
GET  /api/projects/{id}/report        → Full project report
```

---

## Simulation & Optimisation Architecture

Both services use a **pluggable interface** pattern:

```
FastAPI Router → service.run_*() → _mock_*()  [current]
                                → _real_*()   [plug in when ready]
```

To connect the real physics engine:
1. Implement `_real_simulation()` in `app/services/simulation_service.py`
2. Set `USE_MOCK_SIMULATION = False`
3. Same pattern applies to `optimization_service.py`

---

## Error Handling

| Scenario                    | HTTP Status | Response                                                    |
|-----------------------------|-------------|-------------------------------------------------------------|
| Project not found           | 404         | `{"detail": "Project not found"}`                           |
| Climate not configured      | 422         | `{"detail": "Climate profile is required..."}`              |
| Shelter not configured      | 422         | `{"detail": "Shelter configuration is required..."}`        |
| Invalid material ID         | 422         | `{"detail": "Material with id=X does not exist"}`           |
| Duplicate material name     | 409         | `{"detail": "Material with name '...' already exists"}`     |
| Simulation failure          | 500         | `{"detail": "Simulation failed: ..."}` + DB status=failed   |
| Pydantic validation error   | 422         | FastAPI standard validation response                        |
