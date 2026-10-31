# Privacy-Preserving Clinical Scribe — Team C Backend

FastAPI service for the existing physician web app. It does **not** redesign the UI. Grounding scores are computed from claim/evidence support. Conflicts are flags for review only (no replacement-drug recommendations).

## Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
python -m pip install -r requirements.txt
copy .env.example .env
# Edit .env and replace YOUR_PASSWORD with the local PostgreSQL password
alembic upgrade head
python scripts\seed_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI: http://localhost:8000/docs  
Health: http://localhost:8000/health

Frontend (separate terminal):

```bash
copy .env.example .env   # sets VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/patients` | Patient roster |
| GET | `/api/patients/{id}` | Patient profile |
| GET | `/api/consultations?patientId=` | Consultations / records |
| GET | `/api/consultations/{id}` | Consultation |
| GET | `/api/transcripts/{id}` | Team A transcript |
| GET | `/api/soap-notes/{id}` | SOAP note |
| PATCH | `/api/soap-notes/{id}` | Edit SOAP (invalidates validation) |
| GET | `/api/validations/{id}` | Grounding result |
| POST | `/api/consultations/{id}/validate` | Revalidate (recomputes score) |
| POST | `/api/consultations/{id}/finalize` | Lock note (requires fresh validation) |
| GET | `/api/consultations/{id}/audit` | Audit trail |
| POST | `/api/exports/pdf` | PDF (base64) |
| POST | `/api/exports/fhir` | FHIR R4 Composition JSON |
| POST | `/api/exports/ehr` | Mock EHR handoff |
| POST | `/api/team-b/ingest/{consultation_id}` | Official Team B patient/SOAP/conflict response |
| POST | `/api/team-b/ingest` | Legacy Team B structured SOAP/claims/entities |

Storage uses PostgreSQL through SQLAlchemy 2.x and Psycopg 3. `app/services/store.py` provides the existing compatibility API, with request-scoped sessions owned by FastAPI dependencies.

## PostgreSQL setup

Create a local `backend/.env` from `.env.example`:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/clinical_scribe_db
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Replace `YOUR_PASSWORD` with the private password for the local PostgreSQL account. Do not commit `.env`. Apply the migration and optionally load stable-ID demo seed records:

```bash
cd backend
alembic upgrade head
python scripts\seed_db.py
```

The seed is repeatable and preserves non-demo records. Re-running it does not truncate or overwrite the database. Use `/health` to verify PostgreSQL connectivity.

## Tests

```bash
cd backend
pytest -q
```
