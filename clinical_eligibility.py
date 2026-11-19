"""Pure non-tomographic clinical eligibility findings for CER-AI.

Eligibility is evaluated outside ectasia scoring and never owns final disposition.
It emits DecisionFinding objects that are combined exactly once by the canonical
finalizer together with Randleman, BAD-D, NICE, PS3, and procedural-safety findings.
No tomography field, ectasia score, or report behavior belongs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from clinical_core.disposition import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    PASS,
    STOP_DEFER,
    DecisionFinding,
)


@dataclass(frozen=True)
class EligibilityResult:
    findings: tuple[DecisionFinding, ...]
    missing: tuple[str, ...]
    notes: tuple[str, ...]


def _tri(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    if text in {"yes", "y", "true", "1"}:
        return "yes"
    if text in {"no", "n", "false", "0"}:
        return "no"
    return "unknown"


def evaluate_eligibility(
    plan: Mapping[str, Any] | None,
    patient_modifiers: Mapping[str, Any] | None,
) -> EligibilityResult:
    """Return documented non-tomographic eligibility findings for one eye."""
    plan = plan or {}
    modifiers = patient_modifiers or {}

    stable = _tri(plan.get("stable"))
    progression = _tri(plan.get("progression"))
    cdva = _tri(plan.get("cdva_below_20_20"))
    eye_rubbing = _tri(modifiers.get("eye_rubbing"))
    family_history = _tri(modifiers.get("family_history"))
    pregnancy = _tri(modifiers.get("pregnancy_nursing"))
    collagen = _tri(modifiers.get("collagen_tissue_disease"))
    drug_usage = _tri(modifiers.get("drug_usage"))
    dry_eye = _tri(modifiers.get("dry_eye"))
    systemic = _tri(modifiers.get("systemic_disease"))

    # The optional clinical eligibility panel was removed from the UI.
    # Absence of its three answers must not imply a reassuring assessment
    # or block tomography-only evaluation.
    clinical_questions_omitted = all(value == "unknown" for value in (stable, progression, cdva))
    prior_unverified = str(plan.get("prior") or "").strip().lower() == "unknown"
    lens_unverified = str(modifiers.get("contact_lens_type") or "").strip().upper() == "UNKNOWN"

    required = {
        "refractive_stability": stable,
        "documented_progression": progression,
        "unexplained_cdva_below_20_20": cdva,
        "eye_rubbing_or_ocular_trauma": eye_rubbing,
        "family_history_keratoconus": family_history,
        "pregnancy_or_nursing": pregnancy,
        "collagen_connective_tissue_disease": collagen,
        "relevant_medication": drug_usage,
        "dry_eye": dry_eye,
        "systemic_disease": systemic,
    }
    if clinical_questions_omitted:
        for key in ("refractive_stability", "documented_progression", "unexplained_cdva_below_20_20"):
            required.pop(key)
    if clinical_questions_omitted and all(value.strip().lower() == "unknown" for value in modifiers.values() if isinstance(value, str)):
        # No clinical questionnaire was administered; this is not a clinical PASS.
        findings = []
        if prior_unverified:
            findings.append(DecisionFinding(
                "prior_cornea_history_unverified", ASSESSMENT_INCOMPLETE,
                "Prior corneal refractive surgery was not assessed; a virgin-cornea surgical clearance cannot be issued.",
            ))
        if lens_unverified:
            findings.append(DecisionFinding(
                "contact_lens_history_unverified", ASSESSMENT_INCOMPLETE,
                "Contact-lens use and washout were not assessed; tomography-based surgical clearance cannot be issued.",
            ))
        return EligibilityResult(tuple(findings), (), ("Clinical eligibility not assessed by CER-AI; surgeon review required.",))
    missing = tuple(key for key, value in required.items() if value == "unknown")

    findings: list[DecisionFinding] = []
    notes: list[str] = []
    if missing:
        findings.append(DecisionFinding(
            "clinical_eligibility",
            ASSESSMENT_INCOMPLETE,
            "Clinical eligibility documentation incomplete: " + ", ".join(missing),
        ))

    if stable == "no" or progression == "yes":
        findings.append(DecisionFinding(
            "refractive_stability",
            STOP_DEFER,
            "Refractive instability or documented progression requires defer/re-evaluation.",
        ))
    if cdva == "yes":
        findings.append(DecisionFinding(
            "unexplained_cdva",
            CAUTION,
            "Unexplained preoperative CDVA below 20/20 requires investigation.",
        ))
    if eye_rubbing == "yes":
        findings.append(DecisionFinding(
            "eye_rubbing_or_ocular_trauma",
            CAUTION,
            "Chronic eye rubbing/repetitive ocular trauma requires caution and surgeon review.",
        ))
    if family_history == "yes":
        findings.append(DecisionFinding(
            "family_history_keratoconus",
            CAUTION,
            "Family history of keratoconus requires caution and surgeon review.",
        ))
    if pregnancy == "yes":
        findings.append(DecisionFinding(
            "pregnancy_nursing",
            STOP_DEFER,
            "Pregnancy or nursing requires separate refractive-surgery eligibility review.",
        ))
    if collagen == "yes":
        findings.append(DecisionFinding(
            "collagen_tissue_disease",
            STOP_DEFER,
            "Collagen/connective-tissue disease requires STOP-DEFER and separate eligibility review.",
        ))
    for key, value, detail in (
        ("relevant_medication", drug_usage, "Relevant medication/drug usage requires medication-specific review."),
        ("dry_eye", dry_eye, "Dry-eye disease requires ocular-surface optimization and eligibility review."),
        ("systemic_disease", systemic, "Systemic disease requires disease-specific refractive-surgery eligibility review."),
    ):
        if value == "yes":
            findings.append(DecisionFinding(key, CAUTION, detail))

    if eye_rubbing == "yes":
        notes.append("Chronic eye rubbing/repetitive ocular trauma present.")
    if family_history == "yes":
        notes.append("Family history of keratoconus present.")

    if prior_unverified:
        findings.append(DecisionFinding(
            "prior_cornea_history_unverified", ASSESSMENT_INCOMPLETE,
            "Prior corneal refractive surgery was not assessed; a virgin-cornea surgical clearance cannot be issued.",
        ))
    if lens_unverified:
        findings.append(DecisionFinding(
            "contact_lens_history_unverified", ASSESSMENT_INCOMPLETE,
            "Contact-lens use and washout were not assessed; tomography-based surgical clearance cannot be issued.",
        ))

    if not findings and not clinical_questions_omitted:
        findings.append(DecisionFinding(
            "clinical_eligibility",
            PASS,
            "Required clinical eligibility items documented with no CER-AI eligibility escalation.",
        ))

    return EligibilityResult(tuple(findings), missing, tuple(notes))
