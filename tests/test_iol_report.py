from io import BytesIO
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from pypdf import PdfReader

from iol_module.engine import evaluate_case
from iol_module.models import IOLCaseInput
from iol_module.power import plan_iol_power
from iol_module.report import IOLReportInput, WARNINGS, axis_endpoints, build_iol_report, selected_values
from test_iol_module import base_payload, power_payload
from test_named_user_ui import make_client


def sample_report(locale="tr", both=True, toric=True, worst=False):
    eyes = []
    name = "Örnek Hasta Şükrü Işık"
    for eye in (["OD", "OS"] if both else ["OS"]):
        args = dict(patient_name=name, eye=eye, k2_d=43.25 if toric else 42.5)
        if toric:
            args.update(selected_lens_id="clareon-panoptix-toric-cnwtt3", astigmatism_type="REGULAR",
                        incision_axis_deg=110, sia_axis_deg=110, sia_d=.25,
                        posterior_cornea={"eye":eye, "source":"PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK",
                                          "k1_d":-5.8, "k2_d":-6.1, "k1_axis_deg":20, "k2_axis_deg":110})
        if worst:
            args["axial_length_mm"] = 21.44
        with patch("iol_module.power._spherical_predictions", return_value=(
                [{"IOL":21., "Rx":0., "IsBestOption":True}], "T2" if worst else "Cooke K6", "K6 unavailable" if worst else None)):
            plan = plan_iol_power(power_payload(**args))
        values = base_payload()
        values.update(patient_name=name, eye=eye, iolm500_k1_axis_deg=20, iolm500_k2_axis_deg=110,
                      iolm500_k2_d=args["k2_d"], astigmatism_type="REGULAR" if toric else None)
        recommendation = evaluate_case(IOLCaseInput.model_validate(values))
        if worst:
            recommendation.warning_codes = list(WARNINGS)
        eyes.append({"eye":eye, "plan":plan, "recommendation":recommendation})
    return IOLReportInput(patient_name=name, patient_age_years=66, locale=locale, eyes=eyes)


@pytest.mark.parametrize("locale", ["tr", "en"])
@pytest.mark.parametrize("both,toric,worst", [(True,True,False),(True,True,True),(False,False,False)])
def test_report_is_one_readable_page_with_exact_outputs(locale, both, toric, worst):
    report = sample_report(locale, both, toric, worst)
    with patch("iol_module.power.plan_iol_power", side_effect=AssertionError("No recalculation")):
        data = build_iol_report(report, "Dr. Hüseyin Cengiz")
    pdf = PdfReader(BytesIO(data))
    assert len(pdf.pages) == 1
    text = pdf.pages[0].extract_text()
    assert report.patient_name in text
    assert "Dr. Hüseyin Cengiz" in text
    assert "21.00 D" in text and "0.00 D" in text
    assert "NAZAL" in text if locale == "tr" else "NASAL" in text
    assert "TEMPORAL" in text
    assert ("TEST ONLY" in text) == toric
    if toric:
        candidate = report.eyes[0].plan.toric_candidates[0]
        assert candidate["model"] in text
        assert f'{candidate["marker_axis_deg"]:.1f}°' in text
    if worst:
        assert "T2" in text and "ESCRS" in text
        assert ("Yüksek alfa" if locale == "tr" else "High alpha") in text


@pytest.mark.parametrize("change", ["patient", "eye", "duplicate", "measurements"])
def test_mixed_or_stale_report_rejected(change):
    body = sample_report().model_dump()
    if change == "patient": body["patient_name"] = "Another patient"
    if change == "eye": body["eyes"][0]["plan"]["inputs"]["eye"] = "OS"
    if change == "duplicate": body["eyes"][1] = body["eyes"][0]
    if change == "measurements": body["eyes"][0]["plan"]["inputs"]["k1_d"] = 45
    with pytest.raises(ValidationError):
        IOLReportInput.model_validate(body)


def test_missing_toric_never_draws_an_axis_and_keeps_spherical_result():
    report = sample_report()
    for item in report.eyes:
        item.plan.toric_candidates = []
        item.plan.toric_status = "INPUTS_INCOMPLETE"
        item.plan.calculation_status = "CALCULATION_UNAVAILABLE"
    with patch("iol_module.report.draw_eye") as draw:
        text = PdfReader(BytesIO(build_iol_report(report))).pages[0].extract_text()
    assert all(call.args[4] is None for call in draw.call_args_list)
    assert "HESAPLANMADI" in text and "21.00 D" in text


def test_ambiguous_spherical_best_never_becomes_an_implant_selection():
    plan = sample_report().eyes[0].plan
    plan.predictions *= 2
    assert selected_values(plan) == (None, None)


def test_zero_axis_is_drawn_and_same_axis_geometry_used_for_both_eyes():
    assert axis_endpoints(100, 100, 40, 0) == (60, 100, 140, 100)
    assert axis_endpoints(100, 100, 40, 90) == pytest.approx((100, 60, 100, 140))
    assert axis_endpoints(100, 100, 40, 30) == pytest.approx((65.358984, 80, 134.641016, 120))
    report = sample_report()
    report.eyes[0].plan.toric_candidates[0]["marker_axis_deg"] = 0
    with patch("iol_module.report.draw_eye") as draw:
        build_iol_report(report)
    assert draw.call_args_list[0].args[4] == 0


def test_report_route_requires_login_and_returns_private_pdf():
    client, core = make_client()
    body = sample_report().model_dump(mode="json")
    assert client.post("/iol/report/pdf", json=body).status_code == 401
    client.cookies.set("cer_ai_session", "valid")
    response = client.post("/iol/report/pdf", json=body)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert response.headers["cache-control"] == "no-store"
    body["eyes"][0]["eye"] = "OS"
    assert client.post("/iol/report/pdf", json=body).status_code == 422
