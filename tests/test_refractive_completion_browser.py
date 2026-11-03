"""Real browser + canonical workflow, with synthetic readings and no external calls."""
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect, sync_playwright

import assessment_workflow as workflow
from test_step11_analyze_completion_workflow import _eye, _plan, _modifiers

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        executable = shutil.which("chromium") or shutil.which("google-chrome") or p.chromium.executable_path
        if not Path(executable).is_file():
            if os.environ.get("CERAI_REFRACTIVE_BROWSER_REQUIRED") == "1":
                pytest.fail("Required refractive browser coverage: Chromium unavailable")
            pytest.skip("Chromium unavailable")
        instance = p.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        yield instance
        instance.close()


@pytest.mark.parametrize("locale,width", [("tr", 390), ("en", 1280)])
def test_completion_corrects_invalid_depth_and_reaches_report_without_reupload(browser, locale, width):
    session = {"extracted": {"eyes": [_eye("OD"), _eye("OS", pachy_thinnest_um=500)]},
               "ready": None, "source_images": []}
    core = SimpleNamespace(APP_VERSION="synthetic-test")
    os_plan = _plan(ablation_um=40., optical_zone_mm=6.5, transition_zone_mm=9.,
                    manifest_entered_sphere_D=.75, manifest_cylinder_signed_D=1.75,
                    intended_entered_sphere_D=.75, intended_cylinder_signed_D=1.75,
                    intended_axis_deg=90.)
    pending = workflow._respond(core, "synthetic-token", session, 21,
                                {"OD": _plan(), "OS": os_plan}, _modifiers(), {"name": "SYNTHETIC QA"}, {})
    assert [(r["eye"], r["key"]) for r in pending["input_requests"]] == [("OS", "lasik_bc_ablation_um")]
    context = browser.new_context(viewport={"width": width, "height": 900}, service_workers="block", reduced_motion="reduce")
    context.add_init_script("localStorage.setItem('cerai-language'," + json.dumps(locale) + ");")
    page = context.new_page()
    requests, errors = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def route_request(route):
        path = urlparse(route.request.url).path
        if path == "/app":
            route.fulfill(content_type="text/html", body=(ROOT / "static/index.html").read_text())
        elif path.startswith("/static/") and path.endswith(".js"):
            route.fulfill(content_type="application/javascript", body=(ROOT / path.lstrip("/")).read_text())
        elif path == "/assessment/complete":
            payload = route.request.post_data_json
            requests.append(payload)
            result = workflow._respond(core, "synthetic-token", session, payload["age"],
                payload["eye_plans"], payload["patient_modifiers"], payload["patient_metadata"],
                payload["clinical_overrides"], payload["source_confirmations"])
            route.fulfill(json=result)
        elif path.startswith("/static/") or path == "/favicon.ico":
            route.fulfill(status=204)
        else:
            raise AssertionError(f"Unexpected external request: {path}")

    page.route("**/*", route_request)
    try:
        page.goto("https://synthetic.test/app")
        page.locator("#imageInput").set_input_files({"name": "synthetic.png", "mimeType": "image/png", "buffer": b"synthetic only"})
        # Seed only the already-read stage; the actual submit handler and canonical
        # /assessment/complete workflow below remain in use.
        page.evaluate("""pending => {
          document.getElementById('patient_name').value='SYNTHETIC QA';
          document.getElementById('age').value='21';
          document.getElementById('contact_lens_type').value='NONE';
          document.querySelector('[name=patient_modifier][value=none]').checked=true;
          for(const eye of ['od','os']){
            const fields={procedure:'LASIK',manifest_sphere:eye==='os'?'.75':'-2',
              manifest_cylinder:eye==='os'?'1.75':'-1',sphere:eye==='os'?'.75':'-2',
              cylinder:eye==='os'?'1.75':'-1',axis:'90',ablation:eye==='os'?'40':'50',flap:'100'};
            for(const [key,value] of Object.entries(fields))document.getElementById(`${eye}_${key}`).value=value;
            document.getElementById(`${eye}_clinical`).open=true;
          }
          readiness.show(pending);
        }""", pending)
        field = page.locator('[data-source-form="os_lasik_bc_ablation_um"]')
        expect(field).to_be_visible()
        for value, reason in [("", "boş" if locale == "tr" else "empty"),
                              ("-1", "en az 0" if locale == "tr" else "at least 0"),
                              ("35.25", "hassasiyet" if locale == "tr" else "precision")]:
            field.fill(value)
            page.locator("#assessBtn").click()
            expect(page.locator("#assessmentProgress")).to_contain_text(reason)
            expect(page.locator("#assessmentProgress")).to_contain_text("OS")
            expect(page.locator("#assessmentProgress")).to_contain_text("6.0")
            expect(field).to_be_focused()
            expect(field).to_have_attribute("aria-invalid", "true")
            expect(field).to_have_value(value)
            expect(page.locator("#os_ablation")).to_have_value("40")
            expect(page.locator("#od_ablation")).to_have_value("50")
            assert requests == []
        field.fill("35")
        page.locator("#assessBtn").click()
        expect(page.locator("#reportCard")).to_be_visible()
        expect(page.locator("#readinessPanel")).to_be_hidden()
        assert len(requests) == 1
        assert requests[0]["eye_plans"]["OS"]["ablation_um"] == 40
        assert requests[0]["eye_plans"]["OS"]["lasik_bc_ablation_um"] == 35
        assert requests[0]["eye_plans"]["OD"]["ablation_um"] == 50
        assert session["ready"] is not None
        assert page.locator("#imageInput").evaluate("el=>el.files.length") == 1
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors, errors
    finally:
        context.close()


@pytest.mark.parametrize("locale,width", [("tr", 390), ("en", 1280)])
def test_numeric_format_range_and_correction_keep_other_answers(browser, locale, width):
    page = browser.new_page(viewport={"width": width, "height": 900})
    try:
        page.set_content('<form novalidate><div class="row"><label>Age</label><input id="age" type="number" min="18" max="120" value="121"></div><div id="panel"></div></form>')
        page.add_script_tag(content=(ROOT / "static/assessment-readiness.js").read_text())
        page.evaluate("""locale => {
          window.CERAI_I18N={locale,translate:value=>value};window.readiness=new HCReadiness(document.getElementById('panel'));
          readiness.show({assessment_token:'synthetic',workflow_status:'NEEDS_INPUT',input_requests:[
            {eye:'OD',key:'I_S',kind:'number',label:'Topometric I-S'},
            {eye:'OS',key:'pachy_thinnest_um',kind:'number',label:'Thinnest pachymetry'}]});
        }""", locale)
        page.locator('#completion_1').fill('not a number')
        page.locator('#completion_2').fill('515')
        error = page.evaluate("() => {try{readiness.collect()}catch(e){return e.message}}")
        assert "OD" in error and "Topometric I-S" in error
        expect(page.locator('#completion_1')).to_have_value('not a number')
        expect(page.locator('#completion_2')).to_have_value('515')
        page.locator('#completion_1').fill('−0,61')
        assert page.evaluate('readiness.collect()') == {'OD': {'I_S': -.61}, 'OS': {'pachy_thinnest_um': 515}}
        message = page.evaluate('readiness.validateForm(document.querySelector("form"))')
        assert '120' in message and 'Age' in message
        page.locator('#age').fill('21')
        assert page.evaluate('readiness.validateForm(document.querySelector("form"))') == ''
        expect(page.locator('#completion_1')).not_to_have_attribute('aria-invalid', 'true')
        assert page.evaluate('readiness.collect()') == {'OD': {'I_S': -.61}, 'OS': {'pachy_thinnest_um': 515}}
    finally:
        page.close()
