"""Canonical Stage 2 IOL power-routing service."""

from __future__ import annotations

import json
import logging
import re
import os
from dataclasses import asdict
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .t2 import predictions as t2_predictions
from .lens_catalog import get_lens, MANUFACTURER_TORIC_REFERENCES
from .models import (
    requires_astigmatism_classification,
    AstigmatismType,
    IOLPowerPlan,
    IOLPowerPlanInput,
    PriorCornealSurgery,
)
from .toric_catalog import VERIFIED_LENS_STEPS
from .toric_formula import ToricBiometry, research_toric_candidates

logger = logging.getLogger("uvicorn.error.iol.power")


class LensThicknessRequired(ValueError):
    """Upstream explicitly requested a measured LT."""


COOKE_K6_URL = os.getenv(
    "COOKE_K6_API_URL", "https://cookeformula.com/api/v1/k6/v2024.01/preop"
)
ESCRS_URL = "https://iolcalculator.escrs.org/"
ASCRS_POST_REFRACTIVE_URL = "https://iolcalc.ascrs.org/"


def _target_from_acd(acd_mm: float) -> float:
    if acd_mm < 2.5:
        return 0.0
    if acd_mm >= 3.5:
        return -0.5
    return -0.25


def _second_formula_required(al_mm: float) -> bool:
    return al_mm < 22.0 or al_mm > 26.0


def _base_inputs(case: IOLPowerPlanInput) -> dict[str, object]:
    values: dict[str, object] = {
        "eye": case.eye,
        "biological_sex": case.biological_sex,
        "axial_length_mm": case.axial_length_mm,
        "acd_mm": case.acd_mm,
        "k1_d": case.k1_d,
        "k1_axis_deg": case.k1_axis_deg,
        "k2_d": case.k2_d,
        "k2_axis_deg": case.k2_axis_deg,
        "astigmatism_d": case.astigmatism_d,
        "target_refraction_d": _target_from_acd(case.acd_mm),
        "prior_corneal_surgery": case.prior_corneal_surgery.value,
    }
    for key, value in {
        "cct_um": case.cct_um,
        "lens_thickness_mm": case.lens_thickness_mm,
        "wtw_mm": case.wtw_mm,
        "incision_axis_deg": case.incision_axis_deg,
        "sia_d": case.sia_d,
        "sia_axis_deg": case.sia_axis_deg,
    }.items():
        if value is not None:
            values[key] = value
    if case.clinical_assessment is not None:
        values["pentacam_pupil_3d_mm"] = case.clinical_assessment.pentacam_pupil_3d_mm
        values["pupil_multifocal_confirmed"] = case.pupil_multifocal_confirmed
    if case.posterior_cornea is not None:
        values["posterior_cornea"] = case.posterior_cornea.model_dump(mode="json")
    return values


def _external_plan(case: IOLPowerPlanInput, lens, *, route: str, name: str, url: str | None, message: str) -> IOLPowerPlan:
    status = "EXTERNAL_REQUIRED" if url else "CALCULATION_UNAVAILABLE"
    return IOLPowerPlan(
        route=route,
        calculation_status=status,
        selected_lens_id=lens.id,
        selected_lens_name=lens.name,
        lens_category=lens.category,
        a_constant=lens.a_constant,
        target_refraction_d=_target_from_acd(case.acd_mm),
        target_locked=True,
        target_warning=None,
        second_formula_required=_second_formula_required(case.axial_length_mm),
        calculator_name=name,
        calculator_url=url,
        escrs_url=ESCRS_URL,
        inputs=_base_inputs(case),
        predictions=[],
        message=message,
    )


def _k6_payload(case: IOLPowerPlanInput, a_constant: float) -> dict[str, object]:
    eye: dict[str, object] = {
        "SpecialSituation": "None",
        "TgtRx": _target_from_acd(case.acd_mm),
        "K1": case.k1_d,
        "K2": case.k2_d,
        "Biometer": "Other",
        "AL": case.axial_length_mm,
        "ACD": case.acd_mm,
    }
    if case.cct_um is not None:
        eye["CCT"] = case.cct_um
    if case.lens_thickness_mm is not None:
        eye["LT"] = case.lens_thickness_mm
    if case.wtw_mm is not None:
        eye["WTW"] = case.wtw_mm
    return {
        "KIndex": 1.3375,
        "PredictionsPerIol": 7,
        "IOLs": [{"AConstant": a_constant, "Family": "Other", "Powers": [{"From": 6, "To": 30, "By": 0.5}]}],
        "Eyes": [eye],
    }


def _k6_failure_reason(exc: Exception) -> str:
    if isinstance(exc, LensThicknessRequired):
        return "Cooke K6 requires measured lens thickness for this calculation. Enter LT or continue at ESCRS if unavailable."
    if isinstance(exc, HTTPError):
        if exc.code == 429:
            return "Cooke K6 request limit reached (HTTP 429). Wait before retrying or continue at ESCRS. This is not a missing LT error."
        return f"Cooke K6 service returned HTTP {exc.code}."
    if isinstance(exc, TimeoutError) or isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError):
        return "Cooke K6 service timed out."
    if isinstance(exc, URLError):
        return "Cooke K6 service could not be reached."
    if isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)):
        return "Cooke K6 service returned an invalid response."
    return str(exc)


def _call_k6(case: IOLPowerPlanInput, a_constant: float) -> list[dict[str, object]]:
    # K6 v2024.01 accepts missing LT/WTW for this standard-eye, Other-biometer
    # route (requested powers are <=30 D). AL <22 mm is not an LT requirement.
    # Prior corneal surgery is routed externally by plan_iol_power.
    raw = json.dumps(_k6_payload(case, a_constant)).encode("utf-8")
    request = Request(
        COOKE_K6_URL,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CER-AI-IOL/1.0",
        },
        method="POST",
    )
    logger.info("k6_request eye=%s lt_present=%s", case.eye, case.lens_thickness_mm is not None)
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning("k6_failure eye=%s http_status=%s lt_present=%s", case.eye, exc.code, case.lens_thickness_mm is not None)
        # Only an explicit validation rejection may request LT. Never infer it
        # from rate limits, short axial length, or a generic service failure.
        if exc.code in (400, 422) and case.lens_thickness_mm is None:
            detail = exc.read(16384).decode("utf-8", errors="replace")
            if re.search(r'(?i)(?:\bLT\b|lens[ _-]*thickness)[\s\"\':=]*(?:is\s+)?(?:required|mandatory|missing)\b', detail):
                raise LensThicknessRequired() from exc
        raise
    eyes = payload.get("Eyes") if isinstance(payload, dict) else payload
    if not isinstance(eyes, list) or not eyes:
        raise ValueError("Cooke K6 returned no eye result.")
    iols = eyes[0].get("IOLs", []) if isinstance(eyes[0], dict) else []
    predictions = iols[0].get("Predictions", []) if isinstance(iols, list) and iols and isinstance(iols[0], dict) else []
    if not isinstance(predictions, list) or not predictions:
        raise ValueError("Cooke K6 returned no power predictions.")
    if any(not isinstance(p, dict) or any(type(p.get(key)) not in (int, float)
           or not isfinite(p[key]) for key in ("IOL", "Rx")) for p in predictions):
        raise ValueError("Cooke K6 returned invalid power predictions.")
    logger.info("k6_success eye=%s predictions=%s lt_present=%s", case.eye, len(predictions), case.lens_thickness_mm is not None)
    return predictions


def _spherical_predictions(case: IOLPowerPlanInput, a_constant: float):
    """K6 first; local T2 only for service/response failures, not validation errors."""
    try:
        return _call_k6(case, a_constant), "Cooke K6", None
    except (HTTPError, URLError, TimeoutError, ValueError, UnicodeDecodeError) as exc:
        if isinstance(exc, LensThicknessRequired):
            raise
        if isinstance(exc, HTTPError) and exc.code in (400, 422):
            raise
        reason = _k6_failure_reason(exc)
        try:
            rows = t2_predictions(case.axial_length_mm, case.k1_d, case.k2_d,
                                  a_constant, _target_from_acd(case.acd_mm))
        except ValueError as t2_error:
            raise ValueError(f"{reason} T2 unavailable: {t2_error}") from t2_error
        logger.info("t2_fallback eye=%s predictions=%s", case.eye, len(rows))
        return rows, "T2", reason


def plan_iol_power(case: IOLPowerPlanInput) -> IOLPowerPlan:
    lens = get_lens(case.selected_lens_id)
    if lens is None:
        raise ValueError("Selected lens is not in the clinic-approved catalog.")
    if case.clinical_assessment is not None:
        from .engine import evaluate_case
        assessment = case.clinical_assessment
        if (assessment.eye != case.eye or assessment.patient_name != case.patient_name
                or assessment.active_k1_d != case.k1_d or assessment.active_k2_d != case.k2_d
                or assessment.iolm500_k1_axis_deg != case.k1_axis_deg
                or assessment.iolm500_k2_axis_deg != case.k2_axis_deg):
            raise ValueError("Clinical assessment does not match the calculation eye or measurements.")
        if lens.category not in evaluate_case(assessment).eligible_categories:
            raise ValueError("Selected lens is excluded by the clinical assessment.")
        if (lens.category == "MULTIFOCAL"
                and not 2.0 <= assessment.pentacam_pupil_3d_mm <= 4.0
                and not case.pupil_multifocal_confirmed):
            raise ValueError("Multifocal selection outside the 2–4 mm pupil target requires surgeon confirmation.")
    toric = requires_astigmatism_classification(case.astigmatism_d) and case.astigmatism_type == AstigmatismType.REGULAR
    if case.prior_corneal_surgery in {
        PriorCornealSurgery.MYOPIC_LASIK_PRK,
        PriorCornealSurgery.HYPEROPIC_LASIK_PRK,
    }:
        history = "history" if case.historical_data_available else "no-history"
        return _external_plan(
            case, lens, route="BARRETT_TRUE_K_EXTERNAL", name="ASCRS post-refractive / Barrett True-K",
            url=ASCRS_POST_REFRACTIVE_URL,
            message=f"Prior LASIK/PRK overrides the standard route. Use the Barrett True-K {history} pathway externally.",
        )
    if case.prior_corneal_surgery == PriorCornealSurgery.RK:
        return _external_plan(
            case, lens, route="POST_RK_EXTERNAL", name="ASCRS post-RK calculator",
            url=ASCRS_POST_REFRACTIVE_URL,
            message="Prior RK requires the external post-RK calculation pathway.",
        )
    if toric:
        inputs = _base_inputs(case)
        try:
            spherical_predictions, formula, fallback_reason = _spherical_predictions(case, lens.a_constant)
        except (HTTPError, URLError, TimeoutError, ValueError, UnicodeDecodeError) as exc:
            return IOLPowerPlan(
                route="MANUFACTURER_TORIC", calculation_status="CALCULATION_UNAVAILABLE",
                selected_lens_id=lens.id, selected_lens_name=lens.name,
                lens_category=lens.category, a_constant=lens.a_constant,
                target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
                target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm),
                calculator_name="Cooke K6 spherical power", calculator_url=lens.toric_calculator_url,
                escrs_url=ESCRS_URL, inputs=inputs, predictions=[],
                toric_status="CALCULATION_UNAVAILABLE",
                required_inputs=["lens_thickness_mm"] if isinstance(exc, LensThicknessRequired) else [],
            message=_k6_failure_reason(exc),
            )
        candidates: list[dict[str, object]] = []
        toric_status = "INPUTS_INCOMPLETE"
        if lens.id not in VERIFIED_LENS_STEPS:
            toric_status = "UNSUPPORTED"
            reference = MANUFACTURER_TORIC_REFERENCES.get(lens.id)
            if reference:
                models = reference.get("models") or ([reference["model"]] if reference.get("model") else [])
                cylinders = reference.get("cylinder_iol_plane_d") or []
                model_text = ", ".join(str(model) for model in models) or "manufacturer series"
                cylinder_text = ", ".join(f"{float(value):.2f}" for value in cylinders)
                explanation = (
                    f"Manufacturer toric reference available ({model_text}; IOL-plane cylinder "
                    f"{cylinder_text} D), but this family is not validated for CER-AI embedded "
                    "axis/model calculation. Use the manufacturer calculator and ESCRS."
                )
            else:
                explanation = (
                    "No verified cylinder model series exists for this lens family in CER-AI. "
                    "Use the manufacturer calculator and ESCRS."
                )
        elif case.posterior_cornea is None or case.cct_um is None:
            explanation = "Same-eye Pentacam 4 Maps Cornea Back K1/K2, a principal axis and Pachy Vertex are required for the embedded toric calculation."
        else:
            best = [p for p in spherical_predictions if p.get("IsBestOption") is True]
            if len(best) != 1 or any(type(best[0].get(key)) not in (int, float)
                                     or not isfinite(best[0][key]) for key in ("IOL", "Rx")):
                toric_status = "CALCULATION_UNAVAILABLE"
                explanation = f"{formula} did not identify one finite best spherical-equivalent power and predicted refraction."
            else:
                posterior = case.posterior_cornea
                try:
                    optical = research_toric_candidates(
                        ToricBiometry(
                            axial_length_mm=case.axial_length_mm,
                            anterior_k1_d=case.k1_d, anterior_k2_d=case.k2_d,
                            anterior_k1_axis_deg=case.k1_axis_deg,
                            posterior_k1_d=posterior.k1_d,
                            posterior_k2_d=posterior.k2_d,
                            posterior_k1_axis_deg=posterior.k1_axis_deg,
                            corneal_thickness_um=case.cct_um,
                            optical_a_constant=lens.a_constant,
                            sia_d=case.sia_d,
                            incision_axis_deg=case.incision_axis_deg,
                        ), lens.id,
                        spherical_equivalent_iol_d=best[0]["IOL"],
                        spherical_predicted_refraction_d=best[0]["Rx"],
                    )
                except (ValueError, ZeroDivisionError, OverflowError) as exc:
                    toric_status = "CALCULATION_UNAVAILABLE"
                    explanation = (str(exc) if str(exc) == "Spherical power is outside the documented toric lens range."
                                   else f"Embedded toric calculation rejected these measurements ({type(exc).__name__}).")
                else:
                    candidates = [asdict(candidate) for candidate in optical]
                    toric_status = "TEST_ONLY"
                    explanation = "Embedded toric model, marker axis and predicted residual are shown for surgeon testing. This hybrid optical model is not clinically validated."
        logger.info("toric_result eye=%s lens=%s status=%s spherical_predictions=%s", case.eye, lens.id, toric_status, len(spherical_predictions))
        return IOLPowerPlan(
            route="MANUFACTURER_TORIC",
            calculation_status="TEST_ONLY" if candidates else "CALCULATION_UNAVAILABLE",
            selected_lens_id=lens.id, selected_lens_name=lens.name,
            lens_category=lens.category, a_constant=lens.a_constant,
            target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
            target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm),
            calculator_name=f"{formula} spherical power", calculator_url=lens.toric_calculator_url,
            spherical_formula=formula, fallback_reason=fallback_reason,
            escrs_url=ESCRS_URL, inputs=inputs, predictions=spherical_predictions,
            toric_candidates=candidates, toric_status=toric_status,
            message=explanation,
        )

    inputs = _base_inputs(case)
    try:
        predictions, formula, fallback_reason = _spherical_predictions(case, lens.a_constant)
    except (HTTPError, URLError, TimeoutError, ValueError, UnicodeDecodeError) as exc:
        return IOLPowerPlan(
            route="COOKE_K6", calculation_status="CALCULATION_UNAVAILABLE",
            selected_lens_id=lens.id, selected_lens_name=lens.name,
            lens_category=lens.category, a_constant=lens.a_constant,
            target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
            target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm), calculator_name="Cooke K6", calculator_url=None,
            escrs_url=ESCRS_URL, inputs=inputs, predictions=[],
            required_inputs=["lens_thickness_mm"] if isinstance(exc, LensThicknessRequired) else [],
            message=_k6_failure_reason(exc),
        )
    return IOLPowerPlan(
        route="T2" if formula == "T2" else "COOKE_K6", calculation_status="COMPLETED",
        selected_lens_id=lens.id, selected_lens_name=lens.name,
        lens_category=lens.category, a_constant=lens.a_constant,
        target_refraction_d=_target_from_acd(case.acd_mm), target_locked=True,
        target_warning=None, second_formula_required=_second_formula_required(case.axial_length_mm), calculator_name=formula, calculator_url=None,
        spherical_formula=formula, fallback_reason=fallback_reason,
        escrs_url=ESCRS_URL, inputs=inputs, predictions=predictions,
        message=f"{formula} calculation completed.",
    )
