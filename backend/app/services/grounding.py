"""Claim grounding against transcript evidence. Scores are always computed."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.models.schemas import (
    Claim,
    Evidence,
    HallucinationRisk,
    MatchType,
    SOAPNote,
    Transcript,
    TranscriptEntry,
    ValidationResult,
)
from app.services.conflicts import detect_conflicts
from app.models.schemas import Patient

SECTIONS = ("subjective", "objective", "assessment", "plan")

STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "at", "by",
    "is", "are", "was", "were", "be", "been", "this", "that", "from", "as", "it",
    "patient", "reports", "confirmed", "daily", "mg", "also", "will", "would",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def hallucination_risk(score: int) -> HallucinationRisk:
    if score >= 90:
        return "low"
    if score >= 70:
        return "moderate"
    return "high"


def compute_grounding(claims: list[Claim]) -> tuple[int, int, int, int, int, HallucinationRisk]:
    total = len(claims)
    supported = sum(1 for c in claims if c.status == "supported")
    unsupported = sum(1 for c in claims if c.status == "unsupported")
    conflicts = sum(1 for c in claims if c.status == "conflict")
    score = 0 if total == 0 else int(round((supported / total) * 100))
    return score, supported, unsupported, conflicts, total, hallucination_risk(score)


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"(\d+)\s+over\s+(\d+)", r"\1/\2", text)
    text = text.replace("degrees celsius", "c").replace("°c", "c")
    text = re.sub(r"[^a-z0-9./]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize(text).split() if t not in STOP and len(t) > 1}


def _distinctive_values(text: str) -> set[str]:
    norm = _normalize(text)
    values = set(re.findall(r"\d+\.\d+", norm))
    values.update(re.findall(r"\d+/\d+", norm))
    return values


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?:\n+\s*\d+\.\s+|\n+|(?<=[.!?])\s+)", text.strip())
    out: list[str] = []
    for p in parts:
        s = p.strip(" \n\t-•")
        if len(s) >= 12:
            out.append(s)
    return out or ([text.strip()] if text.strip() else [])


def extract_claims_from_soap(soap: SOAPNote) -> list[Claim]:
    claims: list[Claim] = []
    for section in SECTIONS:
        body = getattr(soap, section).text
        for i, sentence in enumerate(_split_sentences(body), start=1):
            claims.append(
                Claim(
                    id=f"cl-{soap.consultation_id}-{section[:3]}-{i}",
                    soap_section=section,  # type: ignore[arg-type]
                    text=sentence,
                    status="pending",
                    severity="low",
                    evidence_ids=[],
                )
            )
    return claims


def _best_evidence(claim_text: str, entries: list[TranscriptEntry], claim_id: str) -> list[Evidence]:
    claim_vals = _distinctive_values(claim_text)
    claim_toks = _tokens(claim_text)
    if not claim_toks:
        return []

    corpus_norm = " ".join(_normalize(e.text) for e in entries)
    if claim_vals and any(v not in corpus_norm for v in claim_vals):
        return []

    scored: list[tuple[float, TranscriptEntry, MatchType]] = []
    for entry in entries:
        etoks = _tokens(entry.text)
        if not etoks:
            continue
        overlap = claim_toks & etoks
        if not overlap:
            continue
        jaccard = len(overlap) / len(claim_toks | etoks)
        coverage = len(overlap) / max(len(claim_toks), 1)
        score = max(jaccard, coverage)
        entry_norm = _normalize(entry.text)
        match: MatchType = "semantic"  # type: ignore[assignment]
        if _normalize(claim_text) in entry_norm or entry_norm in _normalize(claim_text):
            match = "exact"
            score = max(score, 0.95)
        if claim_vals and all(v in entry_norm for v in claim_vals):
            score = max(score, 0.9)
            match = "exact" if match == "exact" else "semantic"
        if score >= 0.22 or coverage >= 0.45:
            scored.append((score, entry, match))

    scored.sort(key=lambda x: x[0], reverse=True)
    evidence: list[Evidence] = []
    for score, entry, match in scored[:2]:
        evidence.append(
            Evidence(
                id=f"ev-{claim_id}-{entry.id}",
                transcript_entry_id=entry.id,
                transcript_text=entry.text,
                speaker=entry.speaker,
                timestamp=entry.timestamp,
                relevance_score=round(min(score, 1.0), 2),
                match_type=match,
            )
        )
    return evidence


def ground_claims(
    claims: list[Claim],
    transcript: Transcript | None,
    existing_evidence: list[Evidence] | None = None,
) -> tuple[list[Claim], list[Evidence]]:
    entries = transcript.entries if transcript else []
    ev_by_id = {e.id: e for e in (existing_evidence or [])}
    out_claims: list[Claim] = []
    out_evidence: list[Evidence] = []

    for claim in claims:
        if claim.status == "conflict":
            out_claims.append(claim.model_copy(update={"evidence_ids": []}))
            continue
        provided = [ev_by_id[i] for i in claim.evidence_ids if i in ev_by_id]
        if provided:
            # Verify provided quotes actually appear in the transcript (or match claim).
            verified: list[Evidence] = []
            for ev in provided:
                if not entries:
                    continue
                entry = next((e for e in entries if e.id == ev.transcript_entry_id), None)
                hay = _normalize(entry.text) if entry else ""
                quote = _normalize(ev.transcript_text)
                if entry and (quote in hay or hay in quote or (_tokens(ev.transcript_text) & _tokens(entry.text))):
                    if _distinctive_values(claim.text) and any(
                        v not in " ".join(_normalize(e.text) for e in entries) for v in _distinctive_values(claim.text)
                    ):
                        continue
                    verified.append(ev)
            evidence = verified
        else:
            evidence = _best_evidence(claim.text, entries, claim.id)

        if evidence:
            status = "supported"
            severity = claim.severity if claim.severity != "critical" else "medium"
            out_claims.append(
                claim.model_copy(
                    update={
                        "status": status,
                        "severity": severity,
                        "evidence_ids": [e.id for e in evidence],
                        "conflict_description": None,
                        "conflicting_entities": None,
                    }
                )
            )
            out_evidence.extend(evidence)
        else:
            note = (
                "This statement could not be grounded in the encounter transcript. "
                "Cite an external source explicitly or remove it if uncertain."
            )
            # Keep a documentation hint only — never a treatment recommendation.
            out_claims.append(
                claim.model_copy(
                    update={
                        "status": "unsupported",
                        "severity": "high" if _distinctive_values(claim.text) else "medium",
                        "evidence_ids": [],
                        "conflict_description": None,
                        "conflicting_entities": None,
                        "suggested_correction": note,
                    }
                )
            )
    # de-dupe evidence ids
    uniq: dict[str, Evidence] = {}
    for e in out_evidence:
        uniq[e.id] = e
    return out_claims, list(uniq.values())


def build_validation(
    consultation_id: str,
    soap: SOAPNote,
    transcript: Transcript | None,
    patient: Patient,
    validation_id: str | None = None,
    source_claims: list[Claim] | None = None,
    source_evidence: list[Evidence] | None = None,
    actor_notes: str | None = None,
) -> ValidationResult:
    if source_claims:
        claims = source_claims
        claims, evidence = ground_claims(claims, transcript, source_evidence)
    else:
        claims = extract_claims_from_soap(soap)
        claims, evidence = ground_claims(claims, transcript, None)

    claims = detect_conflicts(patient, claims)
    score, supported, unsupported, conflicts, total, risk = compute_grounding(claims)

    return ValidationResult(
        id=validation_id or f"val-{uuid.uuid4().hex[:8]}",
        consultation_id=consultation_id,
        soap_note_version=soap.version,
        claims=claims,
        evidence=evidence,
        grounding_score=score,
        hallucination_risk=risk,
        supported_count=supported,
        unsupported_count=unsupported,
        conflict_count=conflicts,
        total_claim_count=total,
        is_stale=False,
        validated_at=now_iso(),
        validation_notes=actor_notes,
    )
