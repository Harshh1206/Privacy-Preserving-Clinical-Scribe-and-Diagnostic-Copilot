"""Allergy / medication conflict flags for physician review.

Never recommends replacement medicines or other clinical decisions.
"""

from __future__ import annotations

import re

from app.models.schemas import Claim, Patient

# Drug-class keywords used only to FLAG a documented allergy vs a mentioned drug.
PENICILLIN_CLASS = (
    "penicillin",
    "amoxicillin",
    "ampicillin",
    "amoxil",
    "augmentin",
    "flucloxacillin",
    "piperacillin",
    "nafcillin",
    "oxacillin",
    "dicloxacillin",
    "ticarcillin",
    "benzylpenicillin",
)

SULFA_CLASS = ("sulfamethoxazole", "sulfadiazine", "bactrim", "co-trimoxazole", "trimethoprim-sulfa")
NSAID_CLASS = ("ibuprofen", "naproxen", "diclofenac", "aspirin", "ketorolac")


ALLERGY_FAMILIES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("penicillin", "penicillins", "beta-lactam"), PENICILLIN_CLASS),
    (("sulfa", "sulfonamide", "sulphonamide"), SULFA_CLASS),
    (("nsaid", "ibuprofen", "aspirin", "nsaids"), NSAID_CLASS),
]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _mentions(haystack: str, needles: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for n in needles:
        if re.search(rf"\b{re.escape(n)}\b", haystack):
            found.append(n)
    return found


def detect_conflicts(patient: Patient, claims: list[Claim]) -> list[Claim]:
    """Mark claims that conflict with documented allergies. Flags only."""
    allergy_blob = _norm(" ".join(patient.allergies))
    if not allergy_blob:
        return claims

    active_families: list[tuple[str, tuple[str, ...]]] = []
    for allergy_terms, drugs in ALLERGY_FAMILIES:
        if _mentions(allergy_blob, allergy_terms):
            active_families.append((allergy_terms[0], drugs))

    if not active_families:
        # Generic: if any allergy token appears as a drug in the plan, still don't auto-map alternatives.
        return claims

    updated: list[Claim] = []
    for claim in claims:
        blob = _norm(claim.text)
        hit_entities: list[str] = []
        allergy_name = None
        for family, drugs in active_families:
            mentioned = _mentions(blob, drugs)
            if mentioned:
                hit_entities.extend(mentioned)
                allergy_name = family

        if hit_entities:
            entities = sorted(set(hit_entities))
            desc = (
                f"Documented {allergy_name} allergy on the patient record. "
                f"The note mentions: {', '.join(entities)}. "
                "This is flagged for physician review only — no therapeutic substitution is recommended by this system."
            )
            updated.append(
                claim.model_copy(
                    update={
                        "status": "conflict",
                        "severity": "critical",
                        "conflict_description": desc,
                        "conflicting_entities": entities + [f"{allergy_name} allergy"],
                        "suggested_correction": None,
                    }
                )
            )
        else:
            # Strip any inbound Team B drug-substitution suggestions.
            if claim.suggested_correction and _looks_like_drug_recommendation(claim.suggested_correction):
                updated.append(claim.model_copy(update={"suggested_correction": None}))
            else:
                updated.append(claim)
    return updated


def _looks_like_drug_recommendation(text: str) -> bool:
    lowered = text.lower()
    verbs = ("consider ", "switch to", "substitute", "alternative", "prescribe ", "replace with")
    return any(v in lowered for v in verbs)
