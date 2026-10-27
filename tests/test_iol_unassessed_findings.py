"""Unasked ocular findings stay unknown across API, calculation and archive."""
from io import BytesIO
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pypdf import PdfReader

from iol_module.engine import evaluate_case
from iol_module.models import IOLCaseInput, IOLRecommendation
from iol_module.power import plan_iol_power
from iol_module.report import IOLReportInput, build_iol_report
from test_iol_archive import setup_archive
from test_iol_module import base_payload, power_payload
from test_iol_report import sample_report


FINDINGS = ("retina_status", "macular_pathology_present", "glaucoma_status",
            "ocular_surface_status", "post_treatment_measurements_stable")


def unassessed_payload(**changes):
    return {**base_payload(), "eye": "OD", "iolm500_k2_d": 42.5,
            "iolm500_k1_axis_deg": 20, "iolm500_k2_axis_deg": 110,
            "ocular_findings_assessment": "NOT_ASSESSED",
            **dict.fromkeys(FINDINGS), **changes}


def unassessed_report(locale="en", **changes):
    assessment = IOLCaseInput.model_validate(unassessed_payload(**changes))
    with patch("iol_module.power._spherical_predictions", return_value=(
            [{"IOL": 21.0, "Rx": 0.0, "IsBestOption": True}], "Cooke K6", None)):
        plan = plan_iol_power(power_payload(patient_name=assessment.patient_name, clinical_assessment=assessment))
    return IOLReportInput(patient_name=assessment.patient_name, patient_age_years=66,
                          locale=locale, eyes=[{"eye": "OD", "plan": plan,
                          "recommendation": evaluate_case(assessment)}])


def test_explicit_unassessed_state_never_implies_absent_pathology():
    case = IOLCaseInput.model_validate(unassessed_payload())
    assert all(case.model_dump()[field] is None for field in FINDINGS)
    recommendation = evaluate_case(case)
    assert recommendation.ocular_findings_assessment == "NOT_ASSESSED"
    assert recommendation.recommendation_scope == "OPTICAL_ONLY"
    assert "WARN_OCULAR_FINDINGS_NOT_ASSESSED" in recommendation.warning_codes
    assert "MF_OPTICAL_PROFILE_ONLY" in recommendation.decisive_reason_codes
    assert "MF_BALANCED_POSITIVE_PROFILE" not in recommendation.decisive_reason_codes
    text = " ".join(recommendation.clinical_explanation)
    assert "left to surgeon assessment" in text
    assert "not clinical suitability" in text
    assert "absent" not in text and "Retinal status is none" not in text


@pytest.mark.parametrize("field,value", [
    ("retina_status", "NONE"), ("retina_status", "SIGNIFICANT"),
    ("macular_pathology_present", False), ("macular_pathology_present", True),
    ("glaucoma_status", "NONE"), ("ocular_surface_status", "NONE"),
    ("post_treatment_measurements_stable", False),
    ("post_treatment_measurements_stable", True),
])
def test_unassessed_rejects_silent_negative_or_conflicting_known_finding(field, value):
    with pytest.raises(ValidationError, match="must remain null"):
        IOLCaseInput.model_validate(unassessed_payload(**{field: value}))


def test_missing_legacy_findings_do_not_implicitly_become_unassessed_or_absent():
    payload = base_payload()
    for field in FINDINGS:
        payload.pop(field)
    with pytest.raises(ValidationError, match="require explicit"):
        IOLCaseInput.model_validate(payload)


@pytest.mark.parametrize("change,warning", [
    ({"retina_status": "SIGNIFICANT"}, "WARN_RETINA_SIGNIFICANT"),
    ({"macular_pathology_present": True}, "WARN_MACULAR_PATHOLOGY"),
    ({"glaucoma_status": "PRESENT"}, "WARN_GLAUCOMA_PRESENT"),
    ({"ocular_surface_status": "MODERATE"}, "WARN_OCULAR_SURFACE_MODERATE"),
])
def test_legacy_known_pathologies_keep_original_exclusions_and_recorded_values(change, warning):
    assessment = IOLCaseInput.model_validate({**base_payload(), "eye": "OD",
        "iolm500_k2_d": 42.5, "iolm500_k1_axis_deg": 20, "iolm500_k2_axis_deg": 110, **change})
    recommendation = evaluate_case(assessment)
    assert recommendation.ocular_findings_assessment == "SURGEON_REPORTED"
    assert recommendation.recommendation_scope == "CLINICAL_AND_OPTICAL"
    assert warning in recommendation.warning_codes
    assert not recommendation.multifocal_eligible
    with pytest.raises(ValueError, match="excluded"):
        plan_iol_power(power_payload(selected_lens_id="clareon-panoptix-cnwtt0", clinical_assessment=assessment))
    with patch("iol_module.power._spherical_predictions", return_value=([], "Cooke K6", None)):
        plan = plan_iol_power(power_payload(clinical_assessment=assessment))
    assert all(plan.inputs["ocular_findings"][key] == value for key, value in change.items())


@pytest.mark.parametrize("change", [
    {"total_corneal_hoa_4mm_um": .51}, {"astigmatism_type": "IRREGULAR"},
])
def test_unassessed_does_not_remove_optical_exclusions(change):
    recommendation = evaluate_case(IOLCaseInput.model_validate(unassessed_payload(**change)))
    assert not recommendation.multifocal_eligible
    assert recommendation.recommendation_scope == "OPTICAL_ONLY"


def test_unassessed_does_not_bypass_regularity_or_pupil_confirmation():
    with pytest.raises(ValidationError, match="greater than 1.00"):
        IOLCaseInput.model_validate(unassessed_payload(iolm500_k2_d=43.01))
    assessment = IOLCaseInput.model_validate(unassessed_payload(pentacam_pupil_3d_mm=4.01))
    with pytest.raises(ValueError, match="requires surgeon confirmation"):
        plan_iol_power(power_payload(selected_lens_id="clareon-panoptix-cnwtt0", clinical_assessment=assessment))


@pytest.mark.parametrize("surgery,route", [("MYOPIC_LASIK_PRK", "BARRETT_TRUE_K_EXTERNAL"),
    ("HYPEROPIC_LASIK_PRK", "BARRETT_TRUE_K_EXTERNAL"), ("RK", "POST_RK_EXTERNAL")])
def test_unassessed_does_not_change_prior_surgery_routing(surgery, route):
    assessment = IOLCaseInput.model_validate(unassessed_payload())
    with patch("iol_module.power._spherical_predictions", side_effect=AssertionError("Must route externally")):
        plan = plan_iol_power(power_payload(clinical_assessment=assessment, prior_corneal_surgery=surgery))
    assert plan.route == route
    assert plan.inputs["ocular_findings_assessment"] == "NOT_ASSESSED"
    assert plan.inputs["recommendation_scope"] == "OPTICAL_ONLY"
    assert plan.inputs["ocular_findings"] == dict.fromkeys(FINDINGS)


@pytest.mark.parametrize("locale,phrase", [("en", "left to surgeon assessment"),
                                           ("tr", "cerrah değerlendirmesine bırakıldı")])
def test_report_omits_generic_unassessed_notice(locale, phrase):
    report = unassessed_report(locale)
    report.eyes[0].recommendation.warning_codes = []
    pdf = PdfReader(BytesIO(build_iol_report(report)))
    assert len(pdf.pages) == 1
    text = " ".join(pdf.pages[0].extract_text().split())
    assert phrase not in text
    assert "21.00 D" in text


@pytest.mark.parametrize("change", ["recommendation", "plan", "scope", "false_finding", "missing_finding"])
def test_report_rejects_mixed_assessment_snapshots(change):
    body = unassessed_report().model_dump(mode="json")
    item = body["eyes"][0]
    if change == "recommendation":
        item["recommendation"]["ocular_findings_assessment"] = "SURGEON_REPORTED"
        item["recommendation"]["recommendation_scope"] = "CLINICAL_AND_OPTICAL"
    if change == "plan":
        item["plan"]["inputs"].pop("ocular_findings_assessment")
    if change == "scope":
        item["recommendation"]["recommendation_scope"] = "CLINICAL_AND_OPTICAL"
    if change == "false_finding":
        item["plan"]["inputs"]["ocular_findings"]["macular_pathology_present"] = False
    if change == "missing_finding":
        item["plan"]["inputs"].pop("ocular_findings")
    with pytest.raises(ValidationError):
        IOLReportInput.model_validate(body)


def test_old_recommendation_snapshots_are_not_relabelled_as_assessed():
    body = sample_report(both=False).model_dump(mode="json")
    item = body["eyes"][0]["recommendation"]
    item.pop("ocular_findings_assessment")
    item.pop("recommendation_scope")
    recommendation = IOLRecommendation.model_validate(item)
    assert recommendation.ocular_findings_assessment is None
    assert recommendation.recommendation_scope is None
    build_iol_report(IOLReportInput.model_validate(body))


def test_bilateral_report_keeps_unassessed_scope_eye_specific():
    report = sample_report(locale="en", both=True, toric=False)
    report.eyes[0] = unassessed_report(patient_name=report.patient_name).eyes[0]
    pdf = PdfReader(BytesIO(build_iol_report(report)))
    assert len(pdf.pages) == 2
    assert "left to surgeon assessment" not in " ".join(pdf.pages[0].extract_text().split())
    assert "left to surgeon assessment" not in " ".join(pdf.pages[1].extract_text().split())
    assert report.eyes[1].recommendation.ocular_findings_assessment == "SURGEON_REPORTED"


@pytest.mark.parametrize("locale,phrase", [("en", "Macular pathology; multifocal excluded"),
                                           ("tr", "Makula patolojisi; multifokal dışlandı")])
def test_historical_known_pathology_warning_is_not_erased(locale, phrase):
    body = sample_report(locale=locale, both=False, toric=False).model_dump(mode="json")
    recommendation = body["eyes"][0]["recommendation"]
    recommendation.pop("ocular_findings_assessment")
    recommendation.pop("recommendation_scope")
    recommendation["warning_codes"] = ["WARN_MACULAR_PATHOLOGY"]
    report = IOLReportInput.model_validate(body)
    text = " ".join(PdfReader(BytesIO(build_iol_report(report))).pages[0].extract_text().split())
    assert phrase in text
    assert "left to surgeon assessment" not in text


def test_api_and_encrypted_archive_roundtrip_preserve_explicit_null_findings():
    client, core = setup_archive()
    response = client.post("/iol/evaluate", json=unassessed_payload())
    assert response.status_code == 200
    assert response.json()["recommendation_scope"] == "OPTICAL_ONLY"
    assert client.post("/iol/evaluate", json=unassessed_payload(macular_pathology_present=False)).status_code == 422
    assessment = unassessed_payload()
    power = power_payload(clinical_assessment=assessment).model_dump(mode="json")
    with patch("iol_module.power._spherical_predictions", return_value=(
            [{"IOL": 21.0, "Rx": 0.0, "IsBestOption": True}], "Cooke K6", None)):
        calculated = client.post("/iol/power/plan", json=power)
    assert calculated.status_code == 200
    assert calculated.json()["inputs"]["ocular_findings"] == dict.fromkeys(FINDINGS)
    body = {"patient_name": assessment["patient_name"], "patient_age_years": 66,
            "eyes": [{"eye": "OD", "plan": calculated.json(), "recommendation": response.json()}],
            "assessment_request_id": str(uuid4())}
    saved_response = client.post("/iol/report/pdf", json=body)
    assert saved_response.status_code == 200
    archive = core._cerai_case_archive_runtime.archive
    case_id = saved_response.headers["X-CERAI-Case-ID"]
    snapshot_key = next(key for key in archive.store.list(f"cases/{case_id}/revisions/") if "assessment-json" in key)
    snapshot = json.loads(archive.get_bytes(snapshot_key))
    saved_eye = snapshot["iol_report"]["eyes"][0]
    assert saved_eye["plan"]["inputs"]["ocular_findings"] == dict.fromkeys(FINDINGS)
    assert saved_eye["recommendation"]["ocular_findings_assessment"] == "NOT_ASSESSED"
    assert saved_eye["recommendation"]["recommendation_scope"] == "OPTICAL_ONLY"
    revision_id = saved_response.headers["X-CERAI-Revision-ID"]
    base = f"/archive/cases/{case_id}/revisions/{revision_id}/report/pdf"
    for locale, phrase in (("en", "left to surgeon assessment"), ("tr", "cerrah değerlendirmesine bırakıldı")):
        pdf = client.get(base + "?locale=" + locale)
        assert pdf.status_code == 200
        assert phrase not in " ".join(PdfReader(BytesIO(pdf.content)).pages[0].extract_text().split())
