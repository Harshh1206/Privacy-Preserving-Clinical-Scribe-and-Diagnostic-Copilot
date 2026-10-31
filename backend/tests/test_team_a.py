import os
import sys
import types
import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.database_models import Consultation, Patient, Transcript
from app.main import app
from app.services.transcription import GroqTranscriber, format_timestamp


@pytest.fixture
def team_a_record():
    suffix = uuid.uuid4().hex[:10]
    ids = {
        "patient": f"qa-team-a-patient-{suffix}",
        "consultation": f"qa-team-a-con-{suffix}",
        "transcript": f"qa-team-a-tx-{suffix}",
        "soap": f"qa-team-a-soap-{suffix}",
    }
    db = SessionLocal()
    try:
        db.add(Patient(
            id=ids["patient"], mrn=f"QA-TA-{suffix}", first_name="TeamA",
            last_name=f"Synthetic-{suffix}", dob="1990-01-01", sex="O",
            allergies=[], conditions=[], medications=[], consultation_count=1,
            privacy_level="standard",
        ))
        db.flush()
        db.add(Consultation(
            id=ids["consultation"], patient_id=ids["patient"],
            date="2026-10-31T09:00:00Z", chief_complaint="Synthetic Team A audio test",
            status="pending-review", physician_id="dr-001", physician_name="Dr. Sarah Chen",
            transcript_id=ids["transcript"], soap_note_id=ids["soap"],
            created_at="2026-10-31T09:00:00Z", updated_at="2026-10-31T09:00:00Z",
            safety_status="CLEAR",
        ))
        db.flush()
        db.add(Transcript(
            id=ids["transcript"], consultation_id=ids["consultation"],
            recorded_at="2026-10-31T09:00:00Z", duration_ms=0, language="en-US",
            processing_status="completed",
        ))
        db.commit()
        yield ids
    finally:
        db.rollback()
        db.query(Transcript).filter(Transcript.consultation_id == ids["consultation"]).delete(synchronize_session=False)
        db.query(Consultation).filter(Consultation.id == ids["consultation"]).delete(synchronize_session=False)
        db.query(Patient).filter(Patient.id == ids["patient"]).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_format_timestamp():
    assert format_timestamp(3661000) == "01:01:01"


def test_groq_transcriber_is_mockable(monkeypatch, tmp_path):
    class FakeTranscriptions:
        def create(self, **kwargs):
            assert kwargs["model"] == "whisper-large-v3-turbo"
            assert kwargs["response_format"] == "verbose_json"
            assert kwargs["timestamp_granularities"] == ["segment"]
            return types.SimpleNamespace(
                language="en",
                segments=[types.SimpleNamespace(
                    start=1.25,
                    end=3.50,
                    text=" Synthetic transcription ",
                    avg_logprob=-0.2,
                )],
            )

    class FakeGroq:
        def __init__(self, api_key):
            assert api_key == "synthetic-test-key"
            self.audio = types.SimpleNamespace(
                transcriptions=FakeTranscriptions(),
            )

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    monkeypatch.setattr("app.services.transcription.settings.groq_api_key", "synthetic-test-key")
    audio_path = tmp_path / "synthetic.wav"
    audio_path.write_bytes(b"RIFFsynthetic")
    result = GroqTranscriber().transcribe(str(audio_path))
    assert result.language == "en"
    assert result.duration_ms == 3500
    assert result.segments[0].text == "Synthetic transcription"
    assert result.segments[0].confidence is None


def test_groq_confidence_normalizes_fraction_and_percentage(monkeypatch, tmp_path):
    from app.services.transcription import GroqTranscriber

    class FakeTranscriptions:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                language="en",
                segments=[
                    types.SimpleNamespace(start=0, end=1, text="Zero", confidence=0),
                    types.SimpleNamespace(start=1, end=2, text="Fraction", confidence=0.875),
                    types.SimpleNamespace(start=2, end=3, text="Percentage", confidence=92.5),
                    types.SimpleNamespace(start=3, end=4, text="Missing", confidence=None),
                ],
            )

    class FakeGroq:
        def __init__(self, api_key):
            self.audio = types.SimpleNamespace(transcriptions=FakeTranscriptions())

    monkeypatch.setitem(sys.modules, "groq", types.SimpleNamespace(Groq=FakeGroq))
    monkeypatch.setattr("app.services.transcription.settings.groq_api_key", "synthetic-test-key")
    audio_path = tmp_path / "synthetic.wav"
    audio_path.write_bytes(b"RIFFsynthetic")
    result = GroqTranscriber().transcribe(str(audio_path))
    assert [segment.confidence for segment in result.segments] == [0.0, 0.875, 0.925, None]


def test_team_a_upload_accepts_valid_audio_and_rejects_extension(team_a_record, monkeypatch):
    def mock_background(consultation_id, audio_path):
        if os.path.exists(audio_path):
            os.unlink(audio_path)

    monkeypatch.setattr("app.routers.team_a._background_transcribe", mock_background)

    with TestClient(app) as client:
        response = client.post(
            f"/api/team-a/transcriptions/{team_a_record['consultation']}",
            files={"audio": ("synthetic.wav", b"RIFFsynthetic", "audio/wav")},
        )
        assert response.status_code == 202
        assert response.json()["processingStatus"] == "processing"

        invalid = client.post(
            f"/api/team-a/transcriptions/{team_a_record['consultation']}",
            files={"audio": ("notes.txt", b"not audio", "text/plain")},
        )
        assert invalid.status_code == 422


def test_team_a_status_endpoint_team_a_record(team_a_record):
    with TestClient(app) as client:
        response = client.get(f"/api/team-a/transcriptions/{team_a_record['consultation']}")
        assert response.status_code == 200
        assert response.json()["consultationId"] == team_a_record["consultation"]


def test_team_a_upload_rejects_empty_audio(team_a_record):
    with TestClient(app) as client:
        response = client.post(
            f"/api/team-a/transcriptions/{team_a_record['consultation']}",
            files={"audio": ("synthetic.wav", b"", "audio/wav")},
        )
        assert response.status_code == 422
        assert "empty" in response.json()["detail"].lower()


def test_pending_status_transitions_to_processing_and_schedules_task(team_a_record, monkeypatch, tmp_path):
    db = SessionLocal()
    try:
        row = db.query(Transcript).filter(
            Transcript.consultation_id == team_a_record["consultation"]
        ).one()
        row.processing_status = "pending"
        db.commit()
    finally:
        db.close()

    scheduled = []
    def mock_background(consultation_id, audio_path):
        scheduled.append((consultation_id, os.path.getsize(audio_path) if os.path.exists(audio_path) else 0))
        if os.path.exists(audio_path):
            os.unlink(audio_path)

    monkeypatch.setattr("app.routers.team_a._background_transcribe", mock_background)
    with TestClient(app) as client:
        response = client.post(
            f"/api/team-a/transcriptions/{team_a_record['consultation']}",
            files={"audio": ("synthetic.webm", b"RIFFsynthetic", "audio/webm")},
        )
        assert response.status_code == 202
        assert response.json()["processingStatus"] == "processing"
        assert scheduled == [(team_a_record["consultation"], len(b"RIFFsynthetic"))]


def test_background_worker_processing_completed(monkeypatch, tmp_path):
    from app.routers import team_a
    from app.services.diarization import DiarizationResult

    audio_path = tmp_path / "synthetic.wav"
    audio_path.write_bytes(b"RIFFsynthetic")
    status_calls = []
    replacement_calls = []

    class FakeStore:
        def set_transcript_processing_status(self, consultation_id, value, **kwargs):
            status_calls.append((value, kwargs))

        def replace_transcript_entries(self, consultation_id, entries, **kwargs):
            replacement_calls.append((entries, kwargs))

    class FakeTranscriber:
        def transcribe(self, path):
            return types.SimpleNamespace(
                language="en",
                duration_ms=3500,
                model_name="whisper-large-v3-turbo",
                segments=[types.SimpleNamespace(
                    start_ms=1250,
                    end_ms=3500,
                    text="Synthetic text",
                    confidence=0.9,
                )],
            )

    monkeypatch.setattr(team_a, "Store", FakeStore)
    monkeypatch.setattr(team_a, "GroqTranscriber", FakeTranscriber)
    monkeypatch.setattr(team_a, "diarize_audio", lambda path: DiarizationResult("disabled", [], None))

    team_a._background_transcribe("con-synthetic-test", str(audio_path))

    assert status_calls[0][0] == "processing"
    assert replacement_calls[0][0][0]["text"] == "Synthetic text"
    assert not audio_path.exists()


def test_background_worker_groq_failure_sets_failed(monkeypatch, tmp_path):
    from app.routers import team_a

    audio_path = tmp_path / "synthetic.wav"
    audio_path.write_bytes(b"RIFFsynthetic")
    status_calls = []

    class FakeStore:
        def set_transcript_processing_status(self, consultation_id, value, **kwargs):
            status_calls.append((value, kwargs))

    class FakeTranscriber:
        def transcribe(self, path):
            raise RuntimeError("Groq transcription service is temporarily unavailable. Try again.")

    monkeypatch.setattr(team_a, "Store", FakeStore)
    monkeypatch.setattr(team_a, "GroqTranscriber", FakeTranscriber)
    team_a._background_transcribe("con-synthetic-test", str(audio_path))

    assert status_calls[0][0] == "processing"
    assert status_calls[-1][0] == "failed"
    assert status_calls[-1][1]["error"].startswith("Groq")
    assert not audio_path.exists()


def test_background_worker_database_failure_sets_failed(monkeypatch, tmp_path):
    from app.routers import team_a
    from app.services.diarization import DiarizationResult

    audio_path = tmp_path / "synthetic.wav"
    audio_path.write_bytes(b"RIFFsynthetic")
    status_calls = []

    class FakeStore:
        def set_transcript_processing_status(self, consultation_id, value, **kwargs):
            status_calls.append((value, kwargs))

        def replace_transcript_entries(self, consultation_id, entries, **kwargs):
            raise RuntimeError("sensitive database internals")

    class FakeTranscriber:
        def transcribe(self, path):
            return types.SimpleNamespace(
                language="en",
                duration_ms=1000,
                model_name="whisper-large-v3-turbo",
                segments=[types.SimpleNamespace(
                    start_ms=0,
                    end_ms=1000,
                    text="Synthetic text",
                    confidence=0.9,
                )],
            )

    monkeypatch.setattr(team_a, "Store", FakeStore)
    monkeypatch.setattr(team_a, "GroqTranscriber", FakeTranscriber)
    monkeypatch.setattr(team_a, "diarize_audio", lambda path: DiarizationResult("disabled", [], None))
    team_a._background_transcribe("con-synthetic-test", str(audio_path))

    assert status_calls[0][0] == "processing"
    assert status_calls[-1][0] == "failed"
    assert status_calls[-1][1]["error"] == "Database persistence failed while saving transcription."


def test_create_patient_and_duplicate_mrn():
    suffix = uuid.uuid4().hex[:10]
    patient_id = None
    db = SessionLocal()
    try:
        with TestClient(app) as client:
            payload = {
                "mrn": f"QA-NEW-{suffix}",
                "firstName": "Synthetic",
                "lastName": f"Patient-{suffix}",
                "dob": "1990-01-01",
                "sex": "O",
                "allergies": [],
                "conditions": [],
                "medications": [],
                "privacyLevel": "standard",
            }
            response = client.post("/api/patients", json=payload)
            assert response.status_code == 201
            patient_id = response.json()["id"]
            assert response.json()["mrn"] == payload["mrn"]

            duplicate = client.post("/api/patients", json=payload)
            assert duplicate.status_code == 409
    finally:
        if patient_id:
            db.query(Patient).filter(Patient.id == patient_id).delete(synchronize_session=False)
            db.commit()
        db.close()


def test_background_worker_assigns_mocked_diarization_speakers(monkeypatch, tmp_path):
    from app.routers import team_a
    from app.services.diarization import SpeakerTurn

    audio_path = tmp_path / "synthetic.wav"
    audio_path.write_bytes(b"RIFFsynthetic")
    replacement_calls = []

    class FakeStore:
        def set_transcript_processing_status(self, consultation_id, value, **kwargs):
            return None

        def replace_transcript_entries(self, consultation_id, entries, **kwargs):
            replacement_calls.append(entries)

    class FakeTranscriber:
        def transcribe(self, path):
            return types.SimpleNamespace(
                language="en",
                duration_ms=4000,
                model_name="whisper-large-v3-turbo",
                segments=[
                    types.SimpleNamespace(start_ms=0, end_ms=1000, text="Doctor text", confidence=None),
                    types.SimpleNamespace(start_ms=1000, end_ms=2000, text="Patient text", confidence=None),
                    types.SimpleNamespace(start_ms=None, end_ms=None, text="Unknown timing", confidence=None),
                ],
            )

    monkeypatch.setattr(team_a, "Store", FakeStore)
    monkeypatch.setattr(team_a, "GroqTranscriber", FakeTranscriber)
    monkeypatch.setattr(
        team_a,
        "diarize_audio",
        lambda path: [
            SpeakerTurn("speaker_0", 0, 1000),
            SpeakerTurn("speaker_1", 1000, 2000),
        ],
    )

    team_a._background_transcribe("con-diarization-test", str(audio_path))

    entries = replacement_calls[-1]
    assert entries[0]["speaker_id"] == "speaker_0"
    assert entries[1]["speaker_id"] == "speaker_1"
    assert entries[2]["speaker_id"] is None
    assert entries[2]["start_time_ms"] is None
    assert entries[2]["speaker_role"] == "unknown"
    assert entries[0]["speaker_display_name"] == "Speaker 1"
    assert entries[1]["speaker_display_name"] == "Speaker 2"


def test_greatest_overlap_uses_positive_overlap_and_leaves_unknown_on_none():
    from app.services.diarization import SpeakerTurn, greatest_overlap_segment, speaker_display_name

    turns = [
        SpeakerTurn("speaker_0", 0, 1000),
        SpeakerTurn("speaker_1", 1000, 2000),
    ]
    assert greatest_overlap_segment(200, 1200, turns).speaker_id == "speaker_0"
    assert greatest_overlap_segment(3000, 4000, turns) is None
    assert speaker_display_name("speaker_0") == "Speaker 1"


def test_diarization_reports_torchaudio_audio_metadata_import_failure(monkeypatch, tmp_path):
    import builtins
    from app.services import diarization

    monkeypatch.setattr(diarization.settings, "team_a_diarization_enabled", True)
    monkeypatch.setattr(diarization.settings, "huggingface_token", "synthetic-token")

    original_import = builtins.__import__

    def incompatible_import(name, *args, **kwargs):
        if name == "pyannote.audio":
            raise AttributeError("module 'torchaudio' has no attribute 'AudioMetaData'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", incompatible_import)
    result = diarization.diarize_audio(str(tmp_path / "synthetic.wav"))

    assert result.status == "failed"
    assert result.turns == []
    assert "incompatible torch and torchaudio" in (result.error or "").lower()


def test_background_worker_persists_transcript_when_diarization_fails(monkeypatch, tmp_path):
    from app.routers import team_a
    from app.services.diarization import DiarizationResult

    audio_path = tmp_path / "synthetic.wav"
    audio_path.write_bytes(b"RIFFsynthetic")
    status_calls = []
    diarization_calls = []
    replacement_calls = []

    class FakeStore:
        def set_transcript_processing_status(self, consultation_id, value, **kwargs):
            status_calls.append((value, kwargs))

        def set_transcript_diarization_status(self, consultation_id, value, **kwargs):
            diarization_calls.append((value, kwargs))

        def replace_transcript_entries(self, consultation_id, entries, **kwargs):
            replacement_calls.append((entries, kwargs))

    class FakeTranscriber:
        def transcribe(self, path):
            return types.SimpleNamespace(
                language="en",
                duration_ms=2000,
                model_name="whisper-large-v3-turbo",
                segments=[types.SimpleNamespace(
                    start_ms=0,
                    end_ms=2000,
                    text="Synthetic text persisted without diarization",
                    confidence=0.9,
                )],
            )

    monkeypatch.setattr(team_a, "Store", FakeStore)
    monkeypatch.setattr(team_a, "GroqTranscriber", FakeTranscriber)
    monkeypatch.setattr(
        team_a,
        "diarize_audio",
        lambda path: DiarizationResult(
            "failed",
            [],
            "Diarization dependency initialization failed. The text transcription remains available.",
        ),
    )

    team_a._background_transcribe("con-diarization-failure-test", str(audio_path))

    assert diarization_calls == [
        ("failed", {"error": "Diarization dependency initialization failed. The text transcription remains available."}),
    ]
    assert replacement_calls[0][0][0]["text"] == "Synthetic text persisted without diarization"
    assert replacement_calls[0][0][0]["speaker_id"] is None
    assert replacement_calls[0][0][0]["speaker_role"] == "unknown"
    assert status_calls[0] == ("processing", {"model_name": "whisper-large-v3-turbo"})
    assert not audio_path.exists()


def test_create_consultation_for_team_a_recording():
    suffix = uuid.uuid4().hex[:10]
    patient_id = f"qa-team-a-create-patient-{suffix}"
    consultation_id = None
    db = SessionLocal()
    try:
        db.add(Patient(
            id=patient_id,
            mrn=f"QA-TA-CREATE-{suffix}",
            first_name="Recording",
            last_name=f"Synthetic-{suffix}",
            dob="1990-01-01",
            sex="O",
            allergies=[],
            conditions=[],
            medications=[],
            consultation_count=0,
        ))
        db.commit()

        with TestClient(app) as client:
            response = client.post("/api/consultations", json={
                "patientId": patient_id,
                "chiefComplaint": "Synthetic recording workflow test",
                "physicianId": "dr-001",
                "physicianName": "Dr. Sarah Chen",
            })
            assert response.status_code == 201
            body = response.json()
            consultation_id = body["id"]
            assert body["patientId"] == patient_id
            assert body["status"] == "in-progress"
            assert body["transcriptId"]
            assert body["soapNoteId"]
    finally:
        if consultation_id:
            db.query(Transcript).filter(Transcript.consultation_id == consultation_id).delete(synchronize_session=False)
            db.query(Consultation).filter(Consultation.id == consultation_id).delete(synchronize_session=False)
        db.query(Patient).filter(Patient.id == patient_id).delete(synchronize_session=False)
        db.commit()
        db.close()
