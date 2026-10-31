from __future__ import annotations

import base64

from fpdf import FPDF

from app.models.schemas import Consultation, Patient, SOAPNote, Transcript, ValidationResult


def _sanitize(val: object) -> str:
    if val is None:
        return ""
    s = str(val)
    replacements = (
        ("↑", "[elevated]"),
        ("▲", "[elevated]"),
        ("↓", "[lowered]"),
        ("▼", "[lowered]"),
        ("°C", " deg C"),
        ("°F", " deg F"),
        ("°", " deg"),
        ("±", "+/-"),
        ("—", "-"),
        ("–", "-"),
        ("“", '"'),
        ("”", '"'),
        ("‘", "'"),
        ("’", "'"),
        ("×", "x"),
        ("…", "..."),
        ("²", "2"),
        ("α", "a"),
        ("β", "b"),
    )
    for a, b in replacements:
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def _write(pdf: FPDF, text: str, h: float = 5) -> None:
    pdf.set_x(pdf.l_margin)
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(usable, h, _sanitize(text))


class ClinicalPDF(FPDF):
    def __init__(self, patient_line: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.patient_line = patient_line
        self.set_auto_page_break(auto=True, margin=18)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 130, 145)
        self.cell(0, 6, self.patient_line, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 225, 230)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(140, 150, 165)
        self.cell(0, 8, f"Confidential clinical record  |  Page {self.page_no()}/{{nb}}", align="C")


def generate_pdf(
    consultation: Consultation,
    patient: Patient,
    soap: SOAPNote,
    validation: ValidationResult | None,
    transcript: Transcript | None,
    include_transcript: bool,
    include_validation: bool,
) -> bytes:
    name = f"{patient.first_name} {patient.last_name}"
    pdf = ClinicalPDF(patient_line=_sanitize(f"Patient: {name} (MRN: {patient.mrn}) | Encounter: {consultation.id}"))
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, "Clinical Encounter Note", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(71, 85, 105)
    status = "FINAL" if soap.is_finalized else "DRAFT NOTE"
    pdf.cell(0, 6, _sanitize(f"Status: {status}  |  {consultation.chief_complaint}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, "Patient", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    _write(
        pdf,
        f"{name}  |  {patient.mrn}  |  DOB {patient.dob}  |  Sex {patient.sex}\n"
        f"Allergies: {'; '.join(patient.allergies) or 'NKDA'}\n"
        f"Conditions: {'; '.join(patient.conditions) or 'None'}\n"
        f"Physician: {consultation.physician_name}  |  Date: {consultation.date}",
    )
    pdf.ln(2)

    for title, section in (
        ("Subjective", soap.subjective.text),
        ("Objective", soap.objective.text),
        ("Assessment", soap.assessment.text),
        ("Plan", soap.plan.text),
    ):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        _write(pdf, section)
        pdf.ln(1)

    if include_validation and validation:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(
            0,
            7,
            _sanitize(
                f"Grounding Report  |  {validation.grounding_score}/100  |  risk {validation.hallucination_risk}"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", "", 9)
        _write(
            pdf,
            f"Supported {validation.supported_count}  |  Unsupported {validation.unsupported_count}  |  "
            f"Conflicts {validation.conflict_count}  |  SOAP v{validation.soap_note_version}",
        )
        for claim in validation.claims:
            extra = f" - {claim.conflict_description}" if claim.conflict_description else ""
            _write(pdf, f"[{claim.status.upper()}] ({claim.soap_section}) {claim.text}{extra}", h=4.5)
        pdf.ln(1)

    if include_transcript and transcript:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Encounter Transcript", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for entry in transcript.entries:
            _write(pdf, f"[{entry.timestamp}] {entry.speaker}: {entry.text}", h=4.5)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.ln(4)
    attestor = soap.finalized_by or consultation.physician_name
    _write(
        pdf,
        f"Attestation: {attestor}. This document may contain AI-drafted text that was reviewed by a physician. "
        "HIPAA-sensitive - do not distribute without authorization.",
        h=4,
    )

    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return bytes(raw)


def pdf_base64(**kwargs) -> str:
    return base64.b64encode(generate_pdf(**kwargs)).decode("ascii")
