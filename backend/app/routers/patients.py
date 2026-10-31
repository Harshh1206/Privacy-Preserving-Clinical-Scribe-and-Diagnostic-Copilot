from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.schemas import Patient
from app.services.store import get_store
from app.database import get_db

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[Patient])
def list_patients(db: Session = Depends(get_db)) -> list[Patient]:
    return get_store(db).list_patients()


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> Patient:
    return get_store(db).get_patient(patient_id)
