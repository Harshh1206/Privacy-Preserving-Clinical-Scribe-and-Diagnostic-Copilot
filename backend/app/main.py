from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.routers.consultations import router as consultations_router
from app.routers.exports import router as exports_router
from app.routers.patients import router as patients_router
from app.routers.records import transcripts_router, validations_router
from app.routers.soap import router as soap_router
from app.routers.team_b import router as team_b_router
from app.services.store import get_store
from app.database import check_database_connection, engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        get_store().seed()
    except Exception as exc:
        raise RuntimeError(
            f"PostgreSQL connection failed: {exc}. "
            "Verify DATABASE_URL, pgAdmin/PostgreSQL service, database name, username, and password."
        ) from exc
    yield


app = FastAPI(
    title="Clinical Scribe — Team C API",
    description=(
        "Physician review backend for the Privacy-Preserving Clinical Scribe. "
        "Accepts Team A transcripts and Team B SOAP/claims JSON. "
        "Grounding scores are computed from claim/evidence support. "
        "Conflicts are flagged for physician review only — this API never recommends replacement medicines."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients_router)
app.include_router(consultations_router)
app.include_router(soap_router)
app.include_router(transcripts_router)
app.include_router(validations_router)
app.include_router(exports_router)
app.include_router(team_b_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    try:
        check_database_connection()
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL is unavailable. Check the server, database, and DATABASE_URL.",
        )
