from __future__ import annotations

import copy
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.data import seed
from app.database import SessionLocal
from app.database_models import (
    AuditEntry as DBAuditEntry,
    EvidenceRecord,
    MedicalEntity as DBMedicalEntity,
    Patient as DBPatient,
    Consultation as DBConsultation,
    SOAPNote as DBSOAPNote,
    Transcript as DBTranscript,
    TranscriptEntry,
    TeamBState,
    ValidationClaim,
    ValidationResult as DBValidationResult,
)
from app.models.schemas import (
    AuditEntry,
    Claim,
    Consultation,
    Evidence,
    MedicalEntity,
    Patient,
    SOAPNote,
    SOAPNotePatch,
    SOAPSection,
    Transcript,
    TranscriptEntry as TranscriptEntrySchema,
    ValidationResult,
)
from app.services.errors import conflict, not_found
from app.services.grounding import build_validation, now_iso


class Store:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def _session(self) -> Session:
        return self.db or SessionLocal()

    def _commit(self, db: Session) -> None:
        if self.db is None:
            db.commit()

    def _close(self, db: Session) -> None:
        if self.db is None:
            db.close()

    def seed(self, reset_demo: bool = False) -> None:
        db = self._session()
        try:
            if reset_demo:
                consultation_ids = [consultation.id for consultation in seed.CONSULTATIONS]
                db.query(DBSOAPNote).filter(DBSOAPNote.consultation_id.in_(consultation_ids)).delete(synchronize_session=False)
                db.query(DBTranscript).filter(DBTranscript.consultation_id.in_(consultation_ids)).delete(synchronize_session=False)
                db.query(DBValidationResult).filter(DBValidationResult.consultation_id.in_(consultation_ids)).delete(synchronize_session=False)
                db.query(DBAuditEntry).filter(DBAuditEntry.consultation_id.in_(consultation_ids)).delete(synchronize_session=False)
                db.query(TeamBState).filter(TeamBState.consultation_id.in_(consultation_ids)).delete(synchronize_session=False)
                db.query(DBMedicalEntity).filter(DBMedicalEntity.consultation_id.in_(consultation_ids)).delete(synchronize_session=False)
                for consultation in seed.CONSULTATIONS:
                    row = db.get(DBConsultation, consultation.id)
                    if row is not None:
                        db.delete(row)
                db.flush()
                for patient in seed.PATIENTS:
                    row = db.get(DBPatient, patient.id)
                    if row is not None:
                        db.delete(row)
                db.flush()

            patients = seed.PATIENTS
            for patient in patients:
                row = db.get(DBPatient, patient.id)
                if row is None:
                    db.add(self._patient_row(patient))
            db.flush()

            for consultation in seed.CONSULTATIONS:
                if db.get(DBConsultation, consultation.id) is None:
                    db.add(self._consultation_row(consultation))
            db.flush()

            for transcript_id, transcript in seed.TRANSCRIPTS.items():
                if db.get(DBTranscript, transcript_id) is None:
                    db.add(self._transcript_row(transcript))
            for soap_id, soap in seed.SOAP_NOTES.items():
                if db.get(DBSOAPNote, soap_id) is None:
                    db.add(self._soap_row(soap))
            db.flush()

            for consultation in seed.CONSULTATIONS:
                if db.get(DBValidationResult, consultation.validation_id or "") is None:
                    soap = seed.SOAP_NOTES[consultation.soap_note_id]
                    patient = next(p for p in seed.PATIENTS if p.id == consultation.patient_id)
                    transcript = seed.TRANSCRIPTS.get(consultation.transcript_id)
                    validation_id = consultation.validation_id or f"val-{consultation.id}"
                    validation = build_validation(
                        consultation_id=consultation.id,
                        soap=soap,
                        transcript=transcript,
                        patient=patient,
                        validation_id=validation_id,
                        source_claims=seed.TEAM_B_CLAIMS.get(consultation.id),
                        source_evidence=seed.TEAM_B_EVIDENCE.get(consultation.id),
                    )
                    if soap.is_finalized:
                        validation.is_stale = False
                    db.add(self._validation_row(validation))
                state = db.get(TeamBState, consultation.id)
                if consultation.id in seed.TEAM_B_CLAIMS and state is None:
                    db.add(TeamBState(
                        consultation_id=consultation.id,
                        claims=[c.model_dump(mode="json", by_alias=True) for c in seed.TEAM_B_CLAIMS[consultation.id]],
                        evidence=[e.model_dump(mode="json", by_alias=True) for e in seed.TEAM_B_EVIDENCE.get(consultation.id, [])],
                        entities=[],
                        soap_version=seed.SOAP_NOTES[consultation.soap_note_id].version,
                    ))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            self._close(db)


    def finalize(self, consultation_id: str, physician_id: str, physician_name: str) -> tuple[Consultation, SOAPNote]:
        db = self._session()
        try:
            con = db.get(DBConsultation, consultation_id)
            if not con: raise not_found("Consultation", consultation_id)
            note = db.get(DBSOAPNote, con.soap_note_id or "")
            if not note: raise not_found("SOAP note", con.soap_note_id or "")
            if note.is_finalized or con.status == "finalized":
                raise conflict("Consultation is already finalized")
            validation = db.get(DBValidationResult, con.validation_id or "")
            if not validation:
                raise conflict("Cannot finalize without a current validation. Revalidate first.")
            if validation.is_stale or validation.soap_note_version != note.version:
                raise conflict("Validation is stale. Revalidate before finalization.")
            ts = now_iso()
            note.is_finalized = True
            note.finalized_at = ts
            note.finalized_by = physician_name
            note.updated_at = ts
            con.status = "finalized"
            con.finalised_at = ts
            con.updated_at = ts
            con.physician_id = physician_id or con.physician_id
            con.physician_name = physician_name or con.physician_name
            db.add(DBAuditEntry(
                id=f"au-{uuid.uuid4().hex[:10]}", consultation_id=consultation_id,
                timestamp=ts, action="finalized", actor=physician_name,
                detail=f"Consultation finalized by {physician_name}. SOAP note v{note.version} locked.",
                soap_version=note.version,
            ))
            db.commit()
            db.refresh(con)
            db.refresh(note)
            return self._consultation(con), self._soap(note)
        except Exception:
            db.rollback()
            raise
        finally:
            self._close(db)

    def update_patient_from_team_b(self, consultation_id: str, updates: dict[str, object]) -> None:
        db = self._session()
        try:
            con = db.get(DBConsultation, consultation_id)
            if not con: raise not_found("Consultation", consultation_id)
            patient = db.get(DBPatient, con.patient_id)
            if not patient: raise not_found("Patient", con.patient_id)
            field_map = {
                "first_name": "first_name", "last_name": "last_name", "dob": "dob",
                "phone": "phone", "allergies": "allergies", "medications": "medications",
            }
            for key, value in updates.items():
                if key in field_map:
                    setattr(patient, field_map[key], value)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            self._close(db)

    def _replace_validation(self, db: Session, result: ValidationResult) -> None:
        existing = db.get(DBValidationResult, result.id)
        if existing:
            existing.claims.clear()
            existing.evidence.clear()
            db.delete(existing)
            db.flush()
        db.add(self._validation_row(result))

    def ingest_team_b(
        self,
        consultation_id: str,
        soap: SOAPNote,
        claims: list[Claim],
        evidence: list[Evidence],
        entities: list[MedicalEntity],
        transcript: Transcript | None,
        safety_status: str | None = None,
    ) -> tuple[Consultation, SOAPNote, ValidationResult]:
        db = self._session()
        try:
            con = db.get(DBConsultation, consultation_id)
            if not con: raise not_found("Consultation", consultation_id)
            existing = db.get(DBSOAPNote, con.soap_note_id or "")
            if existing and existing.is_finalized:
                raise conflict("Cannot ingest Team B payload into a finalized consultation")
            stored = existing or DBSOAPNote(id=con.soap_note_id or "", consultation_id=consultation_id)
            stored.id = con.soap_note_id or soap.id
            stored.consultation_id = consultation_id
            stored.subjective = soap.subjective.model_dump()
            stored.objective = soap.objective.model_dump()
            stored.assessment = soap.assessment.model_dump()
            stored.plan = soap.plan.model_dump()
            stored.is_finalized = False
            stored.finalized_at = None
            stored.finalized_by = None
            stored.updated_at = now_iso()
            if not stored.created_at:
                stored.created_at = now_iso()
            db.add(stored)

            if transcript:
                old = db.get(DBTranscript, con.transcript_id or "")
                if old:
                    old.entries.clear()
                    db.delete(old)
                    db.flush()
                db.add(self._transcript_row(transcript.model_copy(update={
                    "id": con.transcript_id or transcript.id,
                    "consultation_id": consultation_id,
                })))

            db.flush()
            state = db.get(TeamBState, consultation_id)
            if state is None:
                state = TeamBState(consultation_id=consultation_id)
            state.claims = [c.model_dump(mode="json", by_alias=True) for c in claims]
            state.evidence = [e.model_dump(mode="json", by_alias=True) for e in evidence]
            state.entities = [e.model_dump(mode="json", by_alias=True) for e in entities]
            state.soap_version = stored.version
            db.add(state)

            for row in db.scalars(select(DBMedicalEntity).where(DBMedicalEntity.consultation_id == consultation_id)).all():
                db.delete(row)
            for entity in entities:
                db.add(DBMedicalEntity(
                    id=entity.id, consultation_id=consultation_id, text=entity.text,
                    type=entity.type, normalized_term=entity.normalized_term,
                    icd_code=entity.icd_code, rx_norm_code=entity.rx_norm_code,
                ))

            patient_row = db.get(DBPatient, con.patient_id)
            transcript_row = db.get(DBTranscript, con.transcript_id or "")
            validation = build_validation(
                consultation_id=consultation_id,
                soap=self._soap(stored),
                transcript=self._transcript(transcript_row) if transcript_row else None,
                patient=self._patient(patient_row) if patient_row else seed.PATIENTS[0],
                validation_id=con.validation_id or f"val-{consultation_id}",
                source_claims=claims,
                source_evidence=evidence,
            )
            self._replace_validation(db, validation)
            con.validation_id = validation.id
            if safety_status is not None:
                con.safety_status = safety_status
            con.updated_at = now_iso()
            db.add(DBAuditEntry(
                id=f"au-{uuid.uuid4().hex[:10]}",
                consultation_id=consultation_id,
                timestamp=now_iso(),
                action="created",
                actor="Team B",
                detail=f"Team B structured payload ingested. SOAP v{stored.version}. Grounding recomputed: {validation.grounding_score}/100.",
                soap_version=stored.version,
            ))
            db.commit()
            db.refresh(con)
            db.refresh(stored)
            return self._consultation(con), self._soap(stored), validation
        except Exception:
            db.rollback()
            raise
        finally:
            self._close(db)

    def get_entities(self, consultation_id: str) -> list[MedicalEntity]:
        db = self._session()
        try:
            state = db.get(TeamBState, consultation_id)
            if state:
                return [MedicalEntity.model_validate(e) for e in state.entities]
            return []
        finally:
            self._close(db)

    def _patient_row(self, p: Patient) -> DBPatient:
        return DBPatient(
            id=p.id, mrn=p.mrn, first_name=p.first_name, last_name=p.last_name,
            dob=p.dob, sex=p.sex, phone=p.phone, allergies=p.allergies,
            conditions=p.conditions, medications=p.medications, last_visit=p.last_visit,
            consultation_count=p.consultation_count, privacy_level=p.privacy_level,
        )

    def _consultation_row(self, c: Consultation) -> DBConsultation:
        return DBConsultation(
            id=c.id, patient_id=c.patient_id, date=c.date, chief_complaint=c.chief_complaint,
            status=c.status, physician_id=c.physician_id, physician_name=c.physician_name,
            duration=c.duration, transcript_id=c.transcript_id, soap_note_id=c.soap_note_id,
            validation_id=c.validation_id, finalised_at=c.finalised_at,
            created_at=c.created_at, updated_at=c.updated_at, safety_status=c.safety_status,
        )

    def _transcript_row(self, t: Transcript) -> DBTranscript:
        row = DBTranscript(
            id=t.id, consultation_id=t.consultation_id, recorded_at=t.recorded_at,
            duration_ms=t.duration_ms, language=t.language,
        )
        row.entries = [
            TranscriptEntry(
                id=e.id, transcript_id=t.id, consultation_id=e.consultation_id,
                timestamp=e.timestamp, offset_ms=e.offset_ms, speaker=e.speaker,
                speaker_role=e.speaker_role, text=e.text,
                linked_claim_ids=e.linked_claim_ids, confidence=e.confidence,
            )
            for e in t.entries
        ]
        return row

    def _soap_row(self, s: SOAPNote) -> DBSOAPNote:
        return DBSOAPNote(
            id=s.id, consultation_id=s.consultation_id,
            subjective=s.subjective.model_dump(), objective=s.objective.model_dump(),
            assessment=s.assessment.model_dump(), plan=s.plan.model_dump(),
            created_at=s.created_at, updated_at=s.updated_at,
            is_finalized=s.is_finalized, finalized_at=s.finalized_at,
            finalized_by=s.finalized_by, version=s.version,
        )

    def _validation_row(self, v: ValidationResult) -> DBValidationResult:
        row = DBValidationResult(
            id=v.id, consultation_id=v.consultation_id, soap_note_version=v.soap_note_version,
            grounding_score=v.grounding_score, hallucination_risk=v.hallucination_risk,
            supported_count=v.supported_count, unsupported_count=v.unsupported_count,
            conflict_count=v.conflict_count, total_claim_count=v.total_claim_count,
            is_stale=v.is_stale, validated_at=v.validated_at, validation_notes=v.validation_notes,
        )
        row.claims = [
            ValidationClaim(
                id=c.id, validation_id=v.id, soap_section=c.soap_section, text=c.text,
                status=c.status, severity=c.severity, evidence_ids=c.evidence_ids,
                conflict_description=c.conflict_description,
                conflicting_entities=c.conflicting_entities,
                suggested_correction=c.suggested_correction,
            ) for c in v.claims
        ]
        row.evidence = [
            EvidenceRecord(
                id=e.id, validation_id=v.id, transcript_entry_id=e.transcript_entry_id,
                transcript_text=e.transcript_text, speaker=e.speaker, timestamp=e.timestamp,
                relevance_score=e.relevance_score, match_type=e.match_type,
            ) for e in v.evidence
        ]
        return row

    def _patient(self, row: DBPatient) -> Patient:
        return Patient.model_validate({
            "id": row.id, "mrn": row.mrn, "firstName": row.first_name,
            "lastName": row.last_name, "dob": row.dob, "sex": row.sex,
            "phone": row.phone, "allergies": row.allergies or [],
            "conditions": row.conditions or [], "medications": row.medications or [],
            "lastVisit": row.last_visit, "consultationCount": row.consultation_count,
            "privacyLevel": row.privacy_level,
        })

    def _consultation(self, row: DBConsultation) -> Consultation:
        return Consultation.model_validate({
            "id": row.id, "patientId": row.patient_id, "date": row.date,
            "chiefComplaint": row.chief_complaint, "status": row.status,
            "physicianId": row.physician_id, "physicianName": row.physician_name,
            "duration": row.duration, "transcriptId": row.transcript_id or "",
            "soapNoteId": row.soap_note_id or "", "validationId": row.validation_id,
            "finalisedAt": row.finalised_at, "createdAt": row.created_at,
            "updatedAt": row.updated_at, "safetyStatus": row.safety_status,
        })

    def _soap(self, row: DBSOAPNote) -> SOAPNote:
        return SOAPNote.model_validate({
            "id": row.id, "consultationId": row.consultation_id,
            "subjective": row.subjective, "objective": row.objective,
            "assessment": row.assessment, "plan": row.plan,
            "createdAt": row.created_at, "updatedAt": row.updated_at,
            "isFinalized": row.is_finalized, "finalizedAt": row.finalized_at,
            "finalizedBy": row.finalized_by, "version": row.version,
        })

    def _transcript(self, row: DBTranscript) -> Transcript:
        entries = [TranscriptEntrySchema.model_validate({
            "id": e.id, "consultationId": e.consultation_id, "timestamp": e.timestamp,
            "offsetMs": e.offset_ms, "speaker": e.speaker, "speakerRole": e.speaker_role,
            "text": e.text, "linkedClaimIds": e.linked_claim_ids, "confidence": e.confidence,
        }) for e in sorted(row.entries, key=lambda x: x.offset_ms)]
        return Transcript.model_validate({
            "id": row.id, "consultationId": row.consultation_id, "entries": entries,
            "recordedAt": row.recorded_at, "durationMs": row.duration_ms, "language": row.language,
        })

    def _validation(self, row: DBValidationResult) -> ValidationResult:
        return ValidationResult.model_validate({
            "id": row.id, "consultationId": row.consultation_id,
            "soapNoteVersion": row.soap_note_version,
            "claims": [{
                "id": c.id, "soapSection": c.soap_section, "text": c.text, "status": c.status,
                "severity": c.severity, "evidenceIds": c.evidence_ids or [],
                "conflictDescription": c.conflict_description,
                "conflictingEntities": c.conflicting_entities,
                "suggestedCorrection": c.suggested_correction,
            } for c in row.claims],
            "evidence": [{
                "id": e.id, "transcriptEntryId": e.transcript_entry_id,
                "transcriptText": e.transcript_text, "speaker": e.speaker,
                "timestamp": e.timestamp, "relevanceScore": e.relevance_score,
                "matchType": e.match_type,
            } for e in row.evidence],
            "groundingScore": row.grounding_score, "hallucinationRisk": row.hallucination_risk,
            "supportedCount": row.supported_count, "unsupportedCount": row.unsupported_count,
            "conflictCount": row.conflict_count, "totalClaimCount": row.total_claim_count,
            "isStale": row.is_stale, "validatedAt": row.validated_at,
            "validationNotes": row.validation_notes,
        })

    def list_patients(self) -> list[Patient]:
        db = self._session()
        try:
            return [self._patient(p) for p in db.scalars(select(DBPatient).order_by(DBPatient.last_name, DBPatient.first_name))]
        finally:
            self._close(db)

    def get_patient(self, patient_id: str) -> Patient:
        db = self._session()
        try:
            row = db.get(DBPatient, patient_id)
            if not row: raise not_found("Patient", patient_id)
            return self._patient(row)
        finally:
            self._close(db)

    def list_consultations(self, patient_id: Optional[str] = None) -> list[Consultation]:
        db = self._session()
        try:
            stmt = select(DBConsultation)
            if patient_id: stmt = stmt.where(DBConsultation.patient_id == patient_id)
            rows = db.scalars(stmt.order_by(DBConsultation.date.desc())).all()
            return [self._consultation(c) for c in rows]
        finally:
            self._close(db)

    def get_consultation(self, consultation_id: str) -> Consultation:
        db = self._session()
        try:
            row = db.get(DBConsultation, consultation_id)
            if not row: raise not_found("Consultation", consultation_id)
            return self._consultation(row)
        finally:
            self._close(db)

    def get_transcript(self, transcript_id: str) -> Transcript:
        db = self._session()
        try:
            row = db.get(DBTranscript, transcript_id)
            if not row: raise not_found("Transcript", transcript_id)
            return self._transcript(row)
        finally:
            self._close(db)

    def get_soap(self, soap_note_id: str) -> SOAPNote:
        db = self._session()
        try:
            row = db.get(DBSOAPNote, soap_note_id)
            if not row: raise not_found("SOAP note", soap_note_id)
            return self._soap(row)
        finally:
            self._close(db)

    def get_validation(self, validation_id: str) -> ValidationResult:
        db = self._session()
        try:
            row = db.get(DBValidationResult, validation_id)
            if not row: raise not_found("Validation", validation_id)
            return self._validation(row)
        finally:
            self._close(db)

    def add_audit(self, consultation_id: str, action: str, actor: str, detail: str, soap_version: int | None = None) -> None:
        db = self._session()
        try:
            if db.get(DBConsultation, consultation_id) is None:
                raise not_found("Consultation", consultation_id)
            db.add(DBAuditEntry(
                id=f"au-{uuid.uuid4().hex[:10]}",
                consultation_id=consultation_id,
                timestamp=now_iso(),
                action=action,
                actor=actor,
                detail=detail,
                soap_version=soap_version,
            ))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            self._close(db)

    def get_audit_trail(self, consultation_id: str) -> list[AuditEntry]:
        db = self._session()
        try:
            if db.get(DBConsultation, consultation_id) is None:
                raise not_found("Consultation", consultation_id)
            rows = db.scalars(
                select(DBAuditEntry)
                .where(DBAuditEntry.consultation_id == consultation_id)
                .order_by(DBAuditEntry.timestamp)
            ).all()
            return [AuditEntry.model_validate({
                "id": r.id, "consultationId": r.consultation_id, "timestamp": r.timestamp,
                "action": r.action, "actor": r.actor, "detail": r.detail,
                "soapVersion": r.soap_version,
            }) for r in rows]
        finally:
            self._close(db)

    def update_soap(self, soap_note_id: str, patch: SOAPNotePatch, actor: str | None = None) -> SOAPNote:
        db = self._session()
        try:
            row = db.get(DBSOAPNote, soap_note_id)
            if not row: raise not_found("SOAP note", soap_note_id)
            if row.is_finalized: raise conflict("Cannot edit a finalized SOAP note")
            ts = now_iso()
            actor = actor or settings.default_physician_name
            for key in ("subjective", "objective", "assessment", "plan"):
                section = getattr(patch, key)
                if section is None:
                    continue
                updated = SOAPSection(
                    text=section.text,
                    last_edited_at=section.last_edited_at or ts,
                    last_edited_by=section.last_edited_by or actor,
                )
                setattr(row, key, updated.model_dump())
            row.version += 1
            row.updated_at = ts
            con = db.get(DBConsultation, row.consultation_id)
            if con:
                con.updated_at = ts
                if con.validation_id:
                    validation = db.get(DBValidationResult, con.validation_id)
                    if validation:
                        validation.is_stale = True
                db.add(DBAuditEntry(
                    id=f"au-{uuid.uuid4().hex[:10]}",
                    consultation_id=row.consultation_id,
                    timestamp=ts,
                    action="edited",
                    actor=actor,
                    detail=f"SOAP note edited. Version bumped to v{row.version}. Previous validation marked stale.",
                    soap_version=row.version,
                ))
            db.commit()
            db.refresh(row)
            return self._soap(row)
        except Exception:
            db.rollback()
            raise
        finally:
            self._close(db)

    def validate_consultation(self, consultation_id: str) -> ValidationResult:
        db = self._session()
        try:
            con = db.get(DBConsultation, consultation_id)
            if not con: raise not_found("Consultation", consultation_id)
            note_row = db.get(DBSOAPNote, con.soap_note_id or "")
            if not note_row: raise not_found("SOAP note", con.soap_note_id or "")
            if note_row.is_finalized: raise conflict("Cannot revalidate a finalized note")
            patient_row = db.get(DBPatient, con.patient_id)
            if not patient_row: raise not_found("Patient", con.patient_id)
            transcript_row = db.get(DBTranscript, con.transcript_id or "")
            state = db.get(TeamBState, consultation_id)
            use_team_b = state is not None and state.soap_version == note_row.version
            source_claims = [Claim.model_validate(c) for c in state.claims] if use_team_b else None
            source_evidence = [Evidence.model_validate(e) for e in state.evidence] if use_team_b else None
            result = build_validation(
                consultation_id=consultation_id,
                soap=self._soap(note_row),
                transcript=self._transcript(transcript_row) if transcript_row else None,
                patient=self._patient(patient_row),
                validation_id=con.validation_id or f"val-{consultation_id}",
                source_claims=copy.deepcopy(source_claims),
                source_evidence=copy.deepcopy(source_evidence),
            )
            existing = db.get(DBValidationResult, result.id)
            if existing:
                existing.claims.clear()
                existing.evidence.clear()
                db.delete(existing)
                db.flush()
            db.add(self._validation_row(result))
            con.validation_id = result.id
            con.updated_at = now_iso()
            db.add(DBAuditEntry(
                id=f"au-{uuid.uuid4().hex[:10]}",
                consultation_id=consultation_id,
                timestamp=now_iso(),
                action="revalidated",
                actor="System",
                detail=f"Revalidation complete. Grounding Score: {result.grounding_score}/100. Risk: {result.hallucination_risk}. Supported {result.supported_count}/{result.total_claim_count}.",
                soap_version=result.soap_note_version,
            ))
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            self._close(db)


_store: Store | None = None


def get_store(db: Session | None = None) -> Store:
    global _store
    if db is not None:
        return Store(db)
    if _store is None:
        _store = Store()
        _store.seed()
    return _store


def reset_store() -> Store:
    global _store
    _store = Store()
    _store.seed(reset_demo=True)
    return _store
