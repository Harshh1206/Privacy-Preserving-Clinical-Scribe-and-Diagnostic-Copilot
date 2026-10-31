from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.schemas import SOAPNote, SOAPNotePatch
from app.services.store import get_store
from app.database import get_db

router = APIRouter(prefix="/api/soap-notes", tags=["soap"])


@router.get("/{soap_note_id}", response_model=SOAPNote)
def get_soap_note(soap_note_id: str, db: Session = Depends(get_db)) -> SOAPNote:
    return get_store(db).get_soap(soap_note_id)


@router.patch("/{soap_note_id}", response_model=SOAPNote)
def update_soap_note(soap_note_id: str, patch: SOAPNotePatch, db: Session = Depends(get_db)) -> SOAPNote:
    return get_store(db).update_soap(soap_note_id, patch)
