from __future__ import annotations

from app.models.schemas import (
    AuditEntry,
    Claim,
    Consultation,
    Evidence,
    Patient,
    SOAPNote,
    SOAPSection,
    Transcript,
    TranscriptEntry,
)

PATIENTS = [
    Patient(
        id="pt-001",
        mrn="MRN-20240001",
        first_name="Eleanor",
        last_name="Hartman",
        dob="1958-03-14",
        sex="F",
        phone="(617) 555-0182",
        allergies=[],
        conditions=["Essential hypertension", "Hyperlipidaemia"],
        medications=["Lisinopril 10 mg daily", "Atorvastatin 40 mg nightly"],
        last_visit="2026-09-14T09:00:00Z",
        consultation_count=7,
        privacy_level="standard",
    ),
    Patient(
        id="pt-002",
        mrn="MRN-20240002",
        first_name="Marcus",
        last_name="Okafor",
        dob="1974-11-29",
        sex="M",
        phone="(617) 555-0247",
        allergies=[],
        conditions=["Type 2 diabetes mellitus", "Obesity"],
        medications=["Metformin 1000 mg BID", "Empagliflozin 10 mg daily"],
        last_visit="2026-09-14T10:15:00Z",
        consultation_count=4,
        privacy_level="standard",
    ),
    Patient(
        id="pt-003",
        mrn="MRN-20240003",
        first_name="Priya",
        last_name="Nair",
        dob="1989-07-07",
        sex="F",
        phone="(617) 555-0318",
        allergies=["Penicillin — anaphylaxis (documented 2019)"],
        conditions=["Upper respiratory infection"],
        medications=[],
        last_visit="2026-09-14T11:30:00Z",
        consultation_count=2,
        privacy_level="standard",
    ),
]

CONSULTATIONS = [
    Consultation(
        id="con-001",
        patient_id="pt-001",
        date="2026-09-14T09:00:00Z",
        chief_complaint="Hypertension follow-up",
        status="pending-review",
        physician_id="dr-001",
        physician_name="Dr. Sarah Chen",
        duration=20,
        transcript_id="tx-001",
        soap_note_id="soap-001",
        validation_id="val-001",
        created_at="2026-09-14T09:00:00Z",
        updated_at="2026-09-14T09:25:00Z",
    ),
    Consultation(
        id="con-002",
        patient_id="pt-002",
        date="2026-09-14T10:15:00Z",
        chief_complaint="Type 2 DM management review",
        status="pending-review",
        physician_id="dr-001",
        physician_name="Dr. Sarah Chen",
        duration=25,
        transcript_id="tx-002",
        soap_note_id="soap-002",
        validation_id="val-002",
        created_at="2026-09-14T10:15:00Z",
        updated_at="2026-09-14T10:45:00Z",
    ),
    Consultation(
        id="con-003",
        patient_id="pt-003",
        date="2026-09-14T11:30:00Z",
        chief_complaint="URI — sore throat, fever",
        status="pending-review",
        physician_id="dr-001",
        physician_name="Dr. Sarah Chen",
        duration=15,
        transcript_id="tx-003",
        soap_note_id="soap-003",
        validation_id="val-003",
        created_at="2026-09-14T11:30:00Z",
        updated_at="2026-09-14T11:50:00Z",
    ),
    Consultation(
        id="con-004",
        patient_id="pt-001",
        date="2026-07-10T09:00:00Z",
        chief_complaint="Hypertension 3-month check",
        status="finalized",
        physician_id="dr-001",
        physician_name="Dr. Sarah Chen",
        duration=18,
        transcript_id="tx-004",
        soap_note_id="soap-004",
        validation_id="val-004",
        finalised_at="2026-07-10T09:40:00Z",
        created_at="2026-07-10T09:00:00Z",
        updated_at="2026-07-10T09:40:00Z",
    ),
]


def _te(i: str, cid: str, ts: str, ms: int, speaker: str, role: str, text: str, conf: float, linked=None) -> TranscriptEntry:
    return TranscriptEntry(
        id=i,
        consultation_id=cid,
        timestamp=ts,
        offset_ms=ms,
        speaker=speaker,
        speaker_role=role,  # type: ignore[arg-type]
        text=text,
        confidence=conf,
        linked_claim_ids=linked,
    )


TRANSCRIPTS = {
    "tx-001": Transcript(
        id="tx-001",
        consultation_id="con-001",
        recorded_at="2026-09-14T09:00:08Z",
        duration_ms=225000,
        language="en-US",
        entries=[
            _te("te-001-1", "con-001", "00:00:08", 8000, "Dr. Chen", "physician", "Good morning Eleanor, how have you been since our last visit?", 0.99),
            _te("te-001-2", "con-001", "00:00:15", 15000, "Eleanor Hartman", "patient", "I've been feeling pretty good overall, but I have noticed some occasional headaches, mostly in the mornings.", 0.97),
            _te("te-001-3", "con-001", "00:00:35", 35000, "Dr. Chen", "physician", "Morning headaches can sometimes be related to blood pressure. Are you still taking the Lisinopril every day?", 0.99),
            _te("te-001-4", "con-001", "00:00:50", 50000, "Eleanor Hartman", "patient", "Yes, every morning without fail. And the Atorvastatin at night too.", 0.98),
            _te("te-001-5", "con-001", "00:01:05", 65000, "Dr. Chen", "physician", "Good. Let me check your blood pressure today. It's reading 148 over 92. That's a bit elevated compared to last time.", 0.99, ["cl-001-3"]),
            _te("te-001-6", "con-001", "00:01:30", 90000, "Eleanor Hartman", "patient", "I've been a bit stressed with work. Could that be causing it?", 0.97),
            _te("te-001-7", "con-001", "00:01:45", 105000, "Dr. Chen", "physician", "Stress definitely plays a role. I also want to check your weight today — you're at 68 kilograms, which is stable.", 0.99, ["cl-001-4"]),
            _te("te-001-8", "con-001", "00:02:10", 130000, "Dr. Chen", "physician", "I'm going to increase the Lisinopril to 20 milligrams daily to get better blood pressure control.", 0.99, ["cl-001-5"]),
            _te("te-001-9", "con-001", "00:02:30", 150000, "Eleanor Hartman", "patient", "Will the higher dose have side effects?", 0.96),
            _te("te-001-10", "con-001", "00:02:40", 160000, "Dr. Chen", "physician", "Watch for a dry cough — that's the most common one. If it becomes bothersome we can switch. Also I'd like you to get a basic metabolic panel before your next visit.", 0.99, ["cl-001-6"]),
            _te("te-001-11", "con-001", "00:03:15", 195000, "Dr. Chen", "physician", "We'll schedule a follow-up in 6 weeks. In the meantime, please monitor your blood pressure at home daily.", 0.99, ["cl-001-7"]),
            _te("te-001-12", "con-001", "00:03:35", 215000, "Eleanor Hartman", "patient", "I understand. Thank you, Doctor.", 0.99),
        ],
    ),
    "tx-002": Transcript(
        id="tx-002",
        consultation_id="con-002",
        recorded_at="2026-09-14T10:15:10Z",
        duration_ms=195000,
        language="en-US",
        entries=[
            _te("te-002-1", "con-002", "00:00:10", 10000, "Dr. Chen", "physician", "Morning Marcus. Let's review your diabetes management today. How has your blood sugar been at home?", 0.99),
            _te("te-002-2", "con-002", "00:00:22", 22000, "Marcus Okafor", "patient", "Honestly not great. My fasting levels have been around 180 to 200 most days. I've been eating better but it's been stressful.", 0.96),
            _te("te-002-3", "con-002", "00:00:50", 50000, "Dr. Chen", "physician", "Those numbers are higher than we'd like. Are you taking the Metformin and Empagliflozin as prescribed?", 0.99),
            _te("te-002-4", "con-002", "00:01:02", 62000, "Marcus Okafor", "patient", "Yes, I take both pills. Metformin twice a day and the other one in the morning.", 0.97),
            _te("te-002-5", "con-002", "00:01:20", 80000, "Dr. Chen", "physician", "Good. Your weight today is 104 kilograms. That's up 2 kilos from last time. Have you been getting regular exercise?", 0.99, ["cl-002-3"]),
            _te("te-002-6", "con-002", "00:01:38", 98000, "Marcus Okafor", "patient", "I walk about 20 minutes a day, maybe 4 or 5 times a week.", 0.97),
            _te("te-002-7", "con-002", "00:02:00", 120000, "Dr. Chen", "physician", "That's a good start. I'd like to increase that to 30 minutes daily if possible. I'm going to refer you to the diabetes educator as well.", 0.99, ["cl-002-5"]),
            _te("te-002-8", "con-002", "00:02:25", 145000, "Dr. Chen", "physician", "We need labs — fasting glucose and a repeat HbA1c. I'd like to see you back in 8 weeks to review the results.", 0.99, ["cl-002-6"]),
            _te("te-002-9", "con-002", "00:02:50", 170000, "Marcus Okafor", "patient", "Okay, I'll try to get the blood work done this week.", 0.97),
            _te("te-002-10", "con-002", "00:03:05", 185000, "Dr. Chen", "physician", "Perfect. Continue current medications for now.", 0.99),
        ],
    ),
    "tx-003": Transcript(
        id="tx-003",
        consultation_id="con-003",
        recorded_at="2026-09-14T11:30:08Z",
        duration_ms=285000,
        language="en-US",
        entries=[
            _te("te-003-1", "con-003", "00:00:08", 8000, "Dr. Chen", "physician", "Hi Priya. What brings you in today?", 0.99),
            _te("te-003-2", "con-003", "00:00:14", 14000, "Priya Nair", "patient", "I've had a really bad sore throat and a fever for the past three days. I feel exhausted and my neck glands are swollen.", 0.97),
            _te("te-003-3", "con-003", "00:00:35", 35000, "Dr. Chen", "physician", "Any cough or runny nose? Headache?", 0.99),
            _te("te-003-4", "con-003", "00:00:42", 42000, "Priya Nair", "patient", "A little bit of a headache, but no cough. Some nasal congestion yesterday.", 0.96),
            _te("te-003-5", "con-003", "00:01:00", 60000, "Dr. Chen", "physician", "Let me have a look at your throat. Your temperature is 38.6 degrees Celsius. Your throat looks quite inflamed — I can see tonsillar exudate. Lymph nodes are palpably enlarged bilaterally.", 0.99, ["cl-003-2"]),
            _te("te-003-6", "con-003", "00:01:40", 100000, "Dr. Chen", "physician", "I'm going to do a rapid strep test right now.", 0.99),
            _te("te-003-7", "con-003", "00:03:15", 195000, "Dr. Chen", "physician", "The strep test is positive. This looks like streptococcal pharyngitis — strep throat.", 0.99, ["cl-003-4"]),
            _te("te-003-8", "con-003", "00:03:35", 215000, "Dr. Chen", "physician", "I'll prescribe amoxicillin 500 milligrams three times a day for 10 days.", 0.99, ["cl-003-5"]),
            _te("te-003-9", "con-003", "00:03:52", 232000, "Priya Nair", "patient", "Is that okay? I feel like I had a reaction to a similar antibiotic once.", 0.93),
            _te("te-003-10", "con-003", "00:04:05", 245000, "Dr. Chen", "physician", "That's important to note. Can you remember which antibiotic it was?", 0.99),
            _te("te-003-11", "con-003", "00:04:15", 255000, "Priya Nair", "patient", "I think it started with a P... penicillin maybe? I had trouble breathing. It was documented somewhere.", 0.92),
            _te("te-003-12", "con-003", "00:04:30", 270000, "Dr. Chen", "physician", "Rest, fluids, ibuprofen or paracetamol for fever. Return if symptoms worsen.", 0.99, ["cl-003-6"]),
        ],
    ),
    "tx-004": Transcript(
        id="tx-004",
        consultation_id="con-004",
        recorded_at="2026-07-10T09:00:00Z",
        duration_ms=180000,
        language="en-US",
        entries=[
            _te("te-004-1", "con-004", "00:00:10", 10000, "Dr. Chen", "physician", "Home readings averaging 130 over 80. Blood pressure today 132 over 84. Weight 67 kilograms. Heart rate 72. Continue Lisinopril 10 milligrams daily. Follow-up in 3 months. Repeat lipid panel in 6 months.", 0.99),
            _te("te-004-2", "con-004", "00:00:40", 40000, "Eleanor Hartman", "patient", "Yes, good blood pressure control at home. Tolerating Lisinopril well. No side effects.", 0.98),
        ],
    ),
}


def _sec(text: str, at: str, by: str = "Dr. Sarah Chen") -> SOAPSection:
    return SOAPSection(text=text, last_edited_at=at, last_edited_by=by)


SOAP_NOTES = {
    "soap-001": SOAPNote(
        id="soap-001",
        consultation_id="con-001",
        subjective=_sec(
            "Patient reports occasional morning headaches since last visit. She denies dizziness, chest pain, or shortness of breath. Medication adherence confirmed — Lisinopril 10 mg daily and Atorvastatin 40 mg nightly. Patient attributes symptoms to increased work-related stress.",
            "2026-09-14T09:22:00Z",
        ),
        objective=_sec(
            "BP: 148/92 mmHg (elevated). Weight: 68 kg (stable). HR: 74 bpm, regular. Respiratory rate: 14/min. No peripheral oedema. Auscultation: clear lung fields bilaterally.",
            "2026-09-14T09:22:00Z",
        ),
        assessment=_sec(
            "Essential hypertension — suboptimally controlled. Likely exacerbated by psychosocial stressors. Hyperlipidaemia — stable on current therapy.",
            "2026-09-14T09:22:00Z",
        ),
        plan=_sec(
            "1. Increase Lisinopril to 20 mg daily for improved BP control.\n2. Monitor for ACE inhibitor-related dry cough; switch to ARB if symptomatic.\n3. Order basic metabolic panel (BMP) — check renal function and electrolytes prior to next visit.\n4. Home BP monitoring daily — log and bring to follow-up.\n5. Follow-up appointment in 6 weeks.\n6. Counsel patient on stress management and lifestyle modification.",
            "2026-09-14T09:22:00Z",
        ),
        created_at="2026-09-14T09:22:00Z",
        updated_at="2026-09-14T09:22:00Z",
        is_finalized=False,
        version=1,
    ),
    "soap-002": SOAPNote(
        id="soap-002",
        consultation_id="con-002",
        subjective=_sec(
            "Patient reports fasting blood glucose readings of 180–200 mg/dL at home. Increased work-related stress identified as contributor. Medication adherence confirmed — Metformin 1000 mg BID and Empagliflozin 10 mg daily. Patient exercising approximately 20 minutes, 4–5 days/week.",
            "2026-09-14T10:42:00Z",
        ),
        objective=_sec(
            "Weight: 104 kg (↑2 kg from last visit). BP: 122/78 mmHg. HR: 80 bpm. BMI: 33.2 kg/m². Last HbA1c result: 9.2% (three months ago — indicates poor glycaemic control).",
            "2026-09-14T10:42:00Z",
        ),
        assessment=_sec(
            "Type 2 diabetes mellitus — suboptimally controlled (HbA1c 9.2%). Obesity — BMI 33.2, weight trending up. Poor glycaemic control likely multifactorial: dietary, psychosocial, and activity-related.",
            "2026-09-14T10:42:00Z",
        ),
        plan=_sec(
            "1. Continue Metformin 1000 mg BID and Empagliflozin 10 mg daily.\n2. Increase physical activity to 30 minutes daily aerobic exercise.\n3. Refer to certified diabetes educator for nutrition and lifestyle counselling.\n4. Order fasting glucose and repeat HbA1c labs.\n5. Follow-up in 8 weeks to review lab results and reassess glycaemic control.",
            "2026-09-14T10:42:00Z",
        ),
        created_at="2026-09-14T10:42:00Z",
        updated_at="2026-09-14T10:42:00Z",
        is_finalized=False,
        version=1,
    ),
    "soap-003": SOAPNote(
        id="soap-003",
        consultation_id="con-003",
        subjective=_sec(
            "Patient presents with 3-day history of severe sore throat, fever, fatigue, and bilateral cervical lymphadenopathy. Reports mild headache and nasal congestion. No significant cough.",
            "2026-09-14T11:48:00Z",
        ),
        objective=_sec(
            "Temperature: 38.6°C. Throat: markedly erythematous with tonsillar exudate bilaterally. Lymph nodes: bilateral cervical lymphadenopathy palpable. Rapid strep antigen test: POSITIVE.",
            "2026-09-14T11:48:00Z",
        ),
        assessment=_sec(
            "Streptococcal pharyngitis (Group A Streptococcus). Acute bacterial tonsillitis.",
            "2026-09-14T11:48:00Z",
        ),
        plan=_sec(
            "1. Prescribe Amoxicillin 500 mg TID × 10 days.\n2. Rest and adequate hydration.\n3. Ibuprofen 400 mg PRN or Paracetamol 500 mg PRN for fever and pain.\n4. Return if symptoms worsen or fail to improve within 48–72 hours.",
            "2026-09-14T11:48:00Z",
        ),
        created_at="2026-09-14T11:48:00Z",
        updated_at="2026-09-14T11:48:00Z",
        is_finalized=False,
        version=1,
    ),
    "soap-004": SOAPNote(
        id="soap-004",
        consultation_id="con-004",
        subjective=_sec(
            "Patient reports good blood pressure control at home with home monitor readings averaging 130/80. Tolerating Lisinopril well. No side effects.",
            "2026-07-10T09:35:00Z",
        ),
        objective=_sec("BP: 132/84 mmHg. Weight: 67 kg. HR: 72 bpm.", "2026-07-10T09:35:00Z"),
        assessment=_sec(
            "Essential hypertension — well controlled on current regimen.",
            "2026-07-10T09:35:00Z",
        ),
        plan=_sec(
            "1. Continue Lisinopril 10 mg daily.\n2. Follow-up in 3 months.\n3. Repeat lipid panel in 6 months.",
            "2026-07-10T09:35:00Z",
        ),
        created_at="2026-07-10T09:35:00Z",
        updated_at="2026-07-10T09:40:00Z",
        is_finalized=True,
        finalized_at="2026-07-10T09:40:00Z",
        finalized_by="Dr. Sarah Chen",
        version=1,
    ),
}

# Team B structured claims/evidence (scores are NOT stored — recomputed on seed/validate)
TEAM_B_CLAIMS: dict[str, list[Claim]] = {
    "con-001": [
        Claim(id="cl-001-1", soap_section="subjective", text="Patient reports occasional morning headaches since last visit.", status="pending", severity="low", evidence_ids=["ev-001-1"]),
        Claim(id="cl-001-2", soap_section="subjective", text="Medication adherence confirmed — Lisinopril 10 mg daily and Atorvastatin 40 mg nightly.", status="pending", severity="low", evidence_ids=["ev-001-2"]),
        Claim(id="cl-001-3", soap_section="objective", text="BP: 148/92 mmHg (elevated).", status="pending", severity="medium", evidence_ids=["ev-001-3"]),
        Claim(id="cl-001-4", soap_section="objective", text="Weight: 68 kg (stable).", status="pending", severity="low", evidence_ids=["ev-001-4"]),
        Claim(id="cl-001-5", soap_section="plan", text="Increase Lisinopril to 20 mg daily for improved BP control.", status="pending", severity="medium", evidence_ids=["ev-001-5"]),
        Claim(id="cl-001-6", soap_section="plan", text="Order basic metabolic panel (BMP).", status="pending", severity="low", evidence_ids=["ev-001-6"]),
        Claim(id="cl-001-7", soap_section="plan", text="Follow-up appointment in 6 weeks.", status="pending", severity="low", evidence_ids=["ev-001-7"]),
    ],
    "con-002": [
        Claim(id="cl-002-1", soap_section="subjective", text="Patient reports fasting blood glucose readings of 180–200 mg/dL at home.", status="pending", severity="low", evidence_ids=["ev-002-1"]),
        Claim(id="cl-002-2", soap_section="subjective", text="Medication adherence confirmed — Metformin 1000 mg BID and Empagliflozin 10 mg daily.", status="pending", severity="low", evidence_ids=["ev-002-2"]),
        Claim(id="cl-002-3", soap_section="objective", text="Weight: 104 kg (↑2 kg from last visit).", status="pending", severity="low", evidence_ids=["ev-002-3"]),
        Claim(id="cl-002-4", soap_section="objective", text="Last HbA1c result: 9.2% (three months ago — indicates poor glycaemic control).", status="pending", severity="high", evidence_ids=[]),
        Claim(id="cl-002-5", soap_section="plan", text="Increase physical activity to 30 minutes daily aerobic exercise.", status="pending", severity="low", evidence_ids=["ev-002-5"]),
        Claim(id="cl-002-6", soap_section="plan", text="Order fasting glucose and repeat HbA1c labs; follow-up in 8 weeks.", status="pending", severity="low", evidence_ids=["ev-002-6"]),
        Claim(id="cl-002-7", soap_section="plan", text="Refer to certified diabetes educator for nutrition and lifestyle counselling.", status="pending", severity="low", evidence_ids=["ev-002-5"]),
    ],
    "con-003": [
        Claim(id="cl-003-1", soap_section="subjective", text="Patient presents with 3-day history of severe sore throat, fever, fatigue, and bilateral cervical lymphadenopathy.", status="pending", severity="low", evidence_ids=["ev-003-1"]),
        Claim(id="cl-003-2", soap_section="objective", text="Temperature: 38.6°C. Throat: markedly erythematous with tonsillar exudate bilaterally.", status="pending", severity="low", evidence_ids=["ev-003-2"]),
        Claim(id="cl-003-3", soap_section="objective", text="Bilateral cervical lymphadenopathy palpable.", status="pending", severity="low", evidence_ids=["ev-003-2"]),
        Claim(id="cl-003-4", soap_section="objective", text="Rapid strep antigen test: POSITIVE.", status="pending", severity="medium", evidence_ids=["ev-003-3"]),
        Claim(id="cl-003-5", soap_section="plan", text="Prescribe Amoxicillin 500 mg TID × 10 days.", status="pending", severity="medium", evidence_ids=["ev-003-4"]),
        Claim(id="cl-003-6", soap_section="plan", text="Rest, adequate hydration, Ibuprofen PRN or Paracetamol PRN for fever and pain.", status="pending", severity="low", evidence_ids=["ev-003-5"]),
    ],
    "con-004": [
        Claim(id="cl-004-1", soap_section="subjective", text="Patient reports good blood pressure control at home with home monitor readings averaging 130/80.", status="pending", severity="low", evidence_ids=[]),
        Claim(id="cl-004-2", soap_section="objective", text="BP: 132/84 mmHg. Weight: 67 kg. HR: 72 bpm.", status="pending", severity="low", evidence_ids=[]),
        Claim(id="cl-004-3", soap_section="assessment", text="Essential hypertension — well controlled on current regimen.", status="pending", severity="low", evidence_ids=[]),
        Claim(id="cl-004-4", soap_section="plan", text="Continue Lisinopril 10 mg daily. Follow-up in 3 months.", status="pending", severity="low", evidence_ids=[]),
    ],
}

TEAM_B_EVIDENCE: dict[str, list[Evidence]] = {
    "con-001": [
        Evidence(id="ev-001-1", transcript_entry_id="te-001-2", transcript_text="I've been feeling pretty good overall, but I have noticed some occasional headaches, mostly in the mornings.", speaker="Eleanor Hartman", timestamp="00:00:15", relevance_score=0.98, match_type="exact"),
        Evidence(id="ev-001-2", transcript_entry_id="te-001-4", transcript_text="Yes, every morning without fail. And the Atorvastatin at night too.", speaker="Eleanor Hartman", timestamp="00:00:50", relevance_score=0.97, match_type="exact"),
        Evidence(id="ev-001-3", transcript_entry_id="te-001-5", transcript_text="It's reading 148 over 92. That's a bit elevated compared to last time.", speaker="Dr. Chen", timestamp="00:01:05", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-001-4", transcript_entry_id="te-001-7", transcript_text="you're at 68 kilograms, which is stable", speaker="Dr. Chen", timestamp="00:01:45", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-001-5", transcript_entry_id="te-001-8", transcript_text="I'm going to increase the Lisinopril to 20 milligrams daily to get better blood pressure control.", speaker="Dr. Chen", timestamp="00:02:10", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-001-6", transcript_entry_id="te-001-10", transcript_text="Watch for a dry cough — that's the most common one. Also I'd like you to get a basic metabolic panel before your next visit.", speaker="Dr. Chen", timestamp="00:02:40", relevance_score=0.99, match_type="exact"),
        Evidence(id="ev-001-7", transcript_entry_id="te-001-11", transcript_text="We'll schedule a follow-up in 6 weeks. In the meantime, please monitor your blood pressure at home daily.", speaker="Dr. Chen", timestamp="00:03:15", relevance_score=1.0, match_type="exact"),
    ],
    "con-002": [
        Evidence(id="ev-002-1", transcript_entry_id="te-002-2", transcript_text="My fasting levels have been around 180 to 200 most days.", speaker="Marcus Okafor", timestamp="00:00:22", relevance_score=0.99, match_type="exact"),
        Evidence(id="ev-002-2", transcript_entry_id="te-002-4", transcript_text="Yes, I take both pills. Metformin twice a day and the other one in the morning.", speaker="Marcus Okafor", timestamp="00:01:02", relevance_score=0.97, match_type="semantic"),
        Evidence(id="ev-002-3", transcript_entry_id="te-002-5", transcript_text="Your weight today is 104 kilograms. That's up 2 kilos from last time.", speaker="Dr. Chen", timestamp="00:01:20", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-002-4", transcript_entry_id="te-002-6", transcript_text="I walk about 20 minutes a day, maybe 4 or 5 times a week.", speaker="Marcus Okafor", timestamp="00:01:38", relevance_score=0.98, match_type="exact"),
        Evidence(id="ev-002-5", transcript_entry_id="te-002-7", transcript_text="I'd like to increase that to 30 minutes daily if possible. I'm going to refer you to the diabetes educator as well.", speaker="Dr. Chen", timestamp="00:02:00", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-002-6", transcript_entry_id="te-002-8", transcript_text="We need labs — fasting glucose and a repeat HbA1c. I'd like to see you back in 8 weeks to review the results.", speaker="Dr. Chen", timestamp="00:02:25", relevance_score=1.0, match_type="exact"),
    ],
    "con-003": [
        Evidence(id="ev-003-1", transcript_entry_id="te-003-2", transcript_text="I've had a really bad sore throat and a fever for the past three days. I feel exhausted and my neck glands are swollen.", speaker="Priya Nair", timestamp="00:00:14", relevance_score=0.99, match_type="exact"),
        Evidence(id="ev-003-2", transcript_entry_id="te-003-5", transcript_text="Your temperature is 38.6 degrees Celsius. Your throat looks quite inflamed — I can see tonsillar exudate. Lymph nodes are palpably enlarged bilaterally.", speaker="Dr. Chen", timestamp="00:01:00", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-003-3", transcript_entry_id="te-003-7", transcript_text="The strep test is positive. This looks like streptococcal pharyngitis — strep throat.", speaker="Dr. Chen", timestamp="00:03:15", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-003-4", transcript_entry_id="te-003-8", transcript_text="I'll prescribe amoxicillin 500 milligrams three times a day for 10 days.", speaker="Dr. Chen", timestamp="00:03:35", relevance_score=1.0, match_type="exact"),
        Evidence(id="ev-003-5", transcript_entry_id="te-003-12", transcript_text="Rest, fluids, ibuprofen or paracetamol for fever. Return if symptoms worsen.", speaker="Dr. Chen", timestamp="00:04:30", relevance_score=0.99, match_type="exact"),
    ],
    "con-004": [],
}

AUDITS = [
    AuditEntry(id="au-001", consultation_id="con-001", timestamp="2026-09-14T09:22:00Z", action="created", actor="System (AI Scribe)", detail="SOAP note v1 generated from transcript tx-001.", soap_version=1),
    AuditEntry(id="au-002", consultation_id="con-001", timestamp="2026-09-14T09:23:00Z", action="validated", actor="System", detail="Initial validation complete (grounding computed from claim/evidence support).", soap_version=1),
    AuditEntry(id="au-003", consultation_id="con-002", timestamp="2026-09-14T10:42:00Z", action="created", actor="System (AI Scribe)", detail="SOAP note v1 generated from transcript tx-002.", soap_version=1),
    AuditEntry(id="au-004", consultation_id="con-002", timestamp="2026-09-14T10:43:00Z", action="validated", actor="System", detail="Initial validation complete (grounding computed from claim/evidence support).", soap_version=1),
    AuditEntry(id="au-005", consultation_id="con-003", timestamp="2026-09-14T11:48:00Z", action="created", actor="System (AI Scribe)", detail="SOAP note v1 generated from transcript tx-003.", soap_version=1),
    AuditEntry(id="au-006", consultation_id="con-003", timestamp="2026-09-14T11:49:00Z", action="validated", actor="System", detail="Initial validation complete (grounding computed from claim/evidence support).", soap_version=1),
    AuditEntry(id="au-007", consultation_id="con-004", timestamp="2026-07-10T09:35:00Z", action="created", actor="System (AI Scribe)", detail="SOAP note v1 generated from transcript tx-004.", soap_version=1),
    AuditEntry(id="au-008", consultation_id="con-004", timestamp="2026-07-10T09:38:00Z", action="validated", actor="System", detail="Initial validation complete.", soap_version=1),
    AuditEntry(id="au-009", consultation_id="con-004", timestamp="2026-07-10T09:40:00Z", action="finalized", actor="Dr. Sarah Chen", detail="Consultation finalized by Dr. Sarah Chen. SOAP note v1 locked.", soap_version=1),
]
