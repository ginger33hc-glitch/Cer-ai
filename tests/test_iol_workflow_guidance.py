"""Local, synthetic browser checks: never upload or submit a clinical case."""
from pathlib import Path
import json
import os
import shutil
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect, sync_playwright

from iol_module.engine import evaluate_case
from iol_module.lens_catalog import public_catalog
from iol_module.models import IOLCaseInput, IOLPowerPlanInput
from iol_module.power import plan_iol_power

ROOT = Path(__file__).resolve().parents[1]
BROWSER = shutil.which("chromium") or shutil.which("google-chrome")
NOTICE = "Ocular pathology was not assessed by CER-AI; left to surgeon assessment. Lens categories reflect optical measurements and preferences only, not clinical suitability."


def source_bundle(differences):
    sources = []
    for eye in differences:
        sources.extend([
            {"extraction": {"document_type": "PENTACAM_CATARACT_PREOP", "eye": eye,
                "pentacam": {"total_corneal_hoa_4mm_um": 0.25, "angle_kappa_mm": 0.2,
                    "angle_alpha_mm": 0.2, "pupil_dia_3d_mm": 3, "cct_pachy_vertex_um": 550, "hwtw_mm": 12}}},
            {"extraction": {"document_type": "PENTACAM_4_MAPS_REFRACTIVE", "eye": eye,
                "cornea_back": {"k1_d": -6, "k2_d": -6.5, "k1_axis_deg": 0, "k2_axis_deg": 90}}},
        ])
    sources.append({"extraction": {"document_type": "IOLMASTER_500_BIOMETRY", "iolmaster500": {
        eye: {"axial_length_mm": 24, "acd_mm": 3, "lens_thickness_mm": 4.5,
              "k1_d": 42, "k2_d": 42 + difference, "k1_axis_deg": 0, "k2_axis_deg": 90}
        for eye, difference in differences.items()}}})
    return {"identity": {"patient_name": "SYNTHETIC QA", "eye": "BOTH" if len(differences) == 2 else next(iter(differences)),
                         "eyes": list(differences)}, "sources": sources}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        executable = BROWSER or p.chromium.executable_path
        if not Path(executable).is_file():
            if os.environ.get("CERAI_IOL_BROWSER_REQUIRED") == "1":
                pytest.fail("Required IOL browser coverage cannot run: Chromium is not installed")
            pytest.skip("Install Chromium to run the local IOL browser checks")
        instance = p.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        yield instance
        instance.close()


def open_workflow(browser, differences, locale="en", width=1440):
    context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
    context.add_init_script("localStorage.setItem('cerai-language'," + json.dumps(locale) + ");"
                            "window.scrolledFields=[]; const nativeScroll=Element.prototype.scrollIntoView; Element.prototype.scrollIntoView=function(options){window.scrolledFields.push(this.id); nativeScroll.call(this,options)};")
    page = context.new_page()
    requests, errors = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def route_request(route):
        path = urlparse(route.request.url).path
        if path == "/iol":
            route.fulfill(content_type="text/html", body=(ROOT / "static/iol.html").read_text().replace("__ASTIGMATISM_THRESHOLD_D__", "1.0"))
        elif path in ("/static/iol.js", "/static/i18n.js", "/static/iol-jobs.js"):
            route.fulfill(content_type="application/javascript", body=(ROOT / path.lstrip("/")).read_text())
        elif path.startswith("/static/"):
            route.fulfill(content_type="application/javascript", body="")
        elif path == "/iol/jobs":
            count = len(route.request.post_data_json["files"])
            route.fulfill(status=202, json={"job_id":"synthetic-job", "status":"UPLOADING", "offsets":[0]*count})
        elif path.startswith("/iol/jobs/synthetic-job/images/"):
            route.fulfill(json={"offset":len(route.request.post_data_buffer)})
        elif path == "/iol/jobs/synthetic-job/start":
            route.fulfill(status=202, json={"status":"COMPLETED", "result":source_bundle(differences)})
        elif path == "/iol/evaluate":
            payload = route.request.post_data_json
            requests.append((path, payload))
            route.fulfill(json=evaluate_case(IOLCaseInput.model_validate(payload)).model_dump(mode="json"))
        elif path == "/iol/lenses":
            route.fulfill(json={"lenses": public_catalog()})
        elif path == "/iol/power/plan":
            payload = route.request.post_data_json
            requests.append((path, payload))
            with patch("iol_module.power._call_k6", return_value=[{"IOL": 20, "Rx": 0, "IsBestOption": True}]):
                plan = plan_iol_power(IOLPowerPlanInput.model_validate(payload))
            route.fulfill(json=plan.model_dump(mode="json"))
        else:
            raise AssertionError(f"Unexpected request: {path}")

    page.route("**/*", route_request)
    page.goto("https://iol.test/iol")
    page.locator("#patientName").fill("SYNTHETIC QA")
    page.locator("#patientAge").fill("66")
    page.locator("#biologicalSex").select_option("Female")
    files = [{"name": f"synthetic-{i}.png", "mimeType": "image/png", "buffer": b"synthetic fixture, never transmitted"}
             for i in range(5 if len(differences) == 2 else 3)]
    page.locator("#sourceImages").set_input_files(files)
    page.locator("#extractButton").click()
    expect(page.locator("#extractButton")).to_be_enabled()
    expect(page.locator("#reviewStage")).to_be_visible()
    return context, page, requests, errors, files


@pytest.mark.parametrize("locale,width", [("en", 1440), ("tr", 390)])
def test_bilateral_required_guidance_and_explicit_unassessed_payload(browser, locale, width):
    context, page, requests, errors, files = open_workflow(browser, {"OD": 1.25, "OS": 1.5}, locale, width)
    try:
        expect(page.locator("#OD-astigType")).to_be_focused()
        expect(page.locator("#recommendAll")).to_be_disabled()
        expect(page.locator("#workflowRequirementList button")).to_have_count(2)
        for eye in ("OD", "OS"):
            expect(page.locator(f"#{eye}-astigType")).to_have_attribute("aria-invalid", "true")
            expect(page.locator(f"#{eye}-astigTypeField")).to_have_class("required-attention")
        assert page.evaluate("window.scrolledFields") == ["OD-astigType"]
        assert page.locator("#OD-astigType").evaluate("el => {const r=el.getBoundingClientRect();return r.top>=0 && r.bottom<=innerHeight;}")
        for field in ("retina", "macular", "glaucoma", "surface", "stable"):
            expect(page.locator(f"#OD-{field}")).to_have_count(0)
        expect(page.locator("#OD-astigTypeHelp")).to_contain_text("1.25")
        if locale == "tr":
            expect(page.locator("#OD-astigTypeHelp")).to_contain_text("Devam etmek için")
            expect(page.locator("#workflowRequirementsTitle")).to_contain_text("zorunlu alanları")
        page.locator("#OD-astigType").select_option("REGULAR")
        expect(page.locator("#recommendAll")).to_be_disabled()
        expect(page.locator("#workflowRequirementList button")).to_have_count(1)
        page.locator("#workflowRequirementList button").click()
        expect(page.locator("#OS-astigType")).to_be_focused()
        page.locator("#OS-astigType").select_option("IRREGULAR")
        expect(page.locator("#workflowRequirements")).to_be_hidden()
        expect(page.locator("#recommendAll")).to_be_enabled()
        page.locator("#recommendAll").click()
        expect(page.locator("#calculateAll")).to_be_enabled()
        expect(page.locator("#OD-recommendation")).to_contain_text("Optik" if locale == "tr" else "Optical")
        assert not page.locator("#OD-priorSurgeryPanel").evaluate("element => element.open")
        expect(page.locator("#OD-priorSurgerySummary")).to_be_visible()
        for _, payload in requests:
            assert payload["ocular_findings_assessment"] == "NOT_ASSESSED"
            assert all(payload[field] is None for field in ("retina_status", "macular_pathology_present", "glaucoma_status", "ocular_surface_status", "post_treatment_measurements_stable"))
        assert {payload["eye"] for _, payload in requests} == {"OD", "OS"}
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.locator("#sourceImages").set_input_files(files)
        expect(page.locator("#workflowRequirements")).to_be_hidden()
        expect(page.locator("#reviewStage")).to_be_hidden()
        page.locator("#extractButton").click()
        expect(page.locator("#OD-astigType")).to_be_focused()
        expect(page.locator("#OD-astigType")).to_have_value("")
        expect(page.locator("#OS-astigType")).to_have_value("")
        expect(page.locator("#workflowRequirementList button")).to_have_count(2)
        assert not errors, errors
    finally:
        context.close()


def test_exact_threshold_and_no_focus_theft_during_typing(browser):
    context, page, requests, errors, _ = open_workflow(browser, {"OD": 1.0, "OS": 1.01})
    try:
        expect(page.locator("#OD-astigTypeField")).to_be_hidden()
        expect(page.locator("#OS-astigType")).to_be_focused()
        expect(page.locator("#workflowRequirementList button")).to_have_count(1)
        assert [payload["eye"] for _, payload in requests] == ["OD"]
        field = page.locator("#OD-k2")
        field.fill("43.25")
        expect(field).to_be_focused()
        assert page.evaluate("window.scrolledFields") == ["OS-astigType"]
        field.press("Tab")
        expect(page.locator("#OD-astigType")).to_be_focused()
        assert page.evaluate("window.scrolledFields") == ["OS-astigType", "OD-astigType"]
        field.fill("43.5")
        field.press("Tab")
        assert page.evaluate("window.scrolledFields") == ["OS-astigType", "OD-astigType"]
        field.fill("43")
        expect(page.locator("#OD-astigTypeField")).to_be_hidden()
        expect(page.locator("#OD-astigType")).to_have_attribute("aria-invalid", "false")
        expect(page.locator("#workflowRequirementList button")).to_have_count(1)
        assert not errors, errors
    finally:
        context.close()


@pytest.mark.parametrize("surgery,history,route_text", [
    ("MYOPIC_LASIK_PRK", "false", "Barrett True-K no-history"),
    ("HYPEROPIC_LASIK_PRK", "true", "Barrett True-K history"),
    ("RK", None, "post-RK"),
])
def test_optional_prior_surgery_panel_preserves_external_routes(browser, surgery, history, route_text):
    context, page, requests, errors, _ = open_workflow(browser, {"OD": 0.75})
    try:
        page.locator("#recommendAll").click()
        expect(page.locator("#calculateAll")).to_be_enabled()
        page.locator("#OD-selectedLens").select_option("clareon-mono-sy60wf")
        page.locator("#OD-priorSurgerySummary").click()
        page.locator("#OD-priorSurgery").select_option(surgery)
        if history is not None:
            expect(page.locator("#OD-historyField")).to_be_visible()
            page.locator("#OD-historicalData").select_option(history)
        else:
            expect(page.locator("#OD-historyField")).to_be_hidden()
        page.locator("#OD-priorSurgerySummary").click()
        expect(page.locator("#OD-priorSurgerySummary")).not_to_have_text("Previous corneal surgery (LASIK/PRK/RK)")
        page.locator("#calculateAll").click()
        expect(page.locator("#OD-powerResult")).to_contain_text(route_text)
        power = [payload for path, payload in requests if path == "/iol/power/plan"][-1]
        assert power["prior_corneal_surgery"] == surgery
        assert power["clinical_assessment"]["ocular_findings_assessment"] == "NOT_ASSESSED"
        assert not errors, errors
    finally:
        context.close()
