from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.schemas import CreatePatientRequest, Patient
from app.services.store import get_store
from app.database import get_db

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[Patient])
def list_patients(db: Session = Depends(get_db)) -> list[Patient]:
    return get_store(db).list_patients()


@router.post("", response_model=Patient, status_code=201)
def create_patient(body: CreatePatientRequest, db: Session = Depends(get_db)) -> Patient:
    return get_store(db).create_patient(
        mrn=body.mrn,
        first_name=body.first_name,
        last_name=body.last_name,
        dob=body.dob,
        sex=body.sex,
        phone=body.phone,
        allergies=body.allergies,
        conditions=body.conditions,
        medications=body.medications,
        privacy_level=body.privacy_level,
    )


@router.get("/{patient_id}", response_model=Patient)
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> Patient:
    return get_store(db).get_patient(patient_id)
