"""Synthetic UI checks. No patient images or upstream model calls."""

import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright, expect

from test_keratoconus import fixture_case
from canonical_runtime_service import _evaluate_keratoconus_case as evaluate_extracted

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "locale,width,needs_input",
    [("en", 1280, False), ("tr", 390, False), ("en", 1280, True), ("tr", 390, True)],
)
def test_screening_browser(locale, width, needs_input):
    extracted, refs = fixture_case()
    result = evaluate_extracted(extracted, refs)
    result["archive"] = {"case_id": "synthetic-case", "revision_id": "synthetic-revision"}
    result["patient"] = {"name": "SYNTHETIC PATIENT", "age": 30}
    pending = {
        "assessment_token": "opaque-test-token",
        "workflow_status": "NEEDS_INPUT",
        "input_requests": [
            {
                "eye": "OD",
                "key": "BAD_D",
                "label": "Final BAD-D",
                "kind": "number",
                "destination": "measurement",
            },
            {
                "eye": "OD",
                "key": "srax",
                "label": "SRAX >20°?",
                "kind": "select",
                "destination": "measurement",
                "options": ["YES", "NO"],
            },
        ],
    }
    with sync_playwright() as p:
        executable = (
            os.environ.get("CERAI_CHROMIUM_EXECUTABLE")
            or shutil.which("chromium")
            or shutil.which("google-chrome")
            or p.chromium.executable_path
        )
        if not Path(executable).is_file():
            pytest.skip("Chromium unavailable")
        browser = p.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": width, "height": 900}, accept_downloads=True)
        context.add_init_script(
            "localStorage.setItem('cerai-language'," + json.dumps(locale) + ");"
        )
        page = context.new_page()
        errors, uploads = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def route(request):
            path = urlparse(request.request.url).path
            if path == "/keratoconus":
                request.fulfill(
                    content_type="text/html",
                    body=(ROOT / "static/keratoconus.html").read_text(),
                )
            elif path == "/static/keratoconus.js":
                request.fulfill(
                    content_type="application/javascript",
                    body=(ROOT / "static/keratoconus.js").read_text(),
                )
            elif path == "/archive/cases/synthetic-case/revisions/synthetic-revision/report/pdf":
                request.fulfill(content_type="application/pdf", body=b"%PDF-1.4 synthetic report")
            elif path == "/keratoconus/stream":
                uploads.append(request.request.post_data_buffer)
                request.fulfill(
                    content_type="application/x-ndjson",
                    body="\n".join(
                        json.dumps(event)
                        for event in [
                            {
                                "type": "progress",
                                "code": "ANALYZING_IMAGES",
                                "percent": 30,
                                "completed_images": 2,
                                "total_images": 5,
                            },
                            {
                                "type": "progress",
                                "code": "CALCULATING_ASSESSMENT"
                                if needs_input
                                else "ARCHIVING",
                                "percent": 85 if needs_input else 95,
                            },
                            {
                                "type": "result",
                                "percent": 85 if needs_input else 100,
                                "result": pending if needs_input else result,
                            },
                        ]
                    )
                    + "\n",
                )
            elif path == "/keratoconus/complete":
                payload = request.request.post_data_json
                assert payload == {
                    "assessment_token": "opaque-test-token",
                    "clinical_overrides": {"OD": {"BAD_D": 1, "srax": "NO"}},
                    "source_confirmations": {},
                }
                request.fulfill(json={**result, "workflow_status": "READY"})
            else:
                request.fulfill(status=404, body="")

        page.route("**/*", route)
        page.goto("http://cerai.test/keratoconus")
        expect(page.locator("h1")).to_have_text(
            "Keratokonus Tarama" if locale == "tr" else "Keratoconus Screening"
        )
        assert page.locator("input[type=number]").count() == 7
        assert (
            page.locator("select").count() == 1
        )  # Language only; no procedure selector.
        page.locator("#patientName").fill("SYNTHETIC PATIENT")
        page.locator("#patientAge").fill("30")
        for eye in ("OD", "OS"):
            page.locator(f"#{eye}_sphere").fill("-3")
            page.locator(f"#{eye}_cylinder").fill("-1")
            page.locator(f"#{eye}_axis").fill("90")
        files = [
            {
                "name": f"synthetic-{i}.png",
                "mimeType": "image/png",
                "buffer": b"synthetic",
            }
            for i in range(5)
        ]
        page.locator("#images").set_input_files(files)
        page.locator("#analyze").click()
        if needs_input:
            expect(page.locator("#completionPanel")).to_be_visible()
            expect(page.locator("#output")).to_be_hidden()
            expect(page.locator("#progressPercent")).to_have_text("85%")
            expect(page.locator("#patientName")).to_have_value("SYNTHETIC PATIENT")
            expect(page.locator("#patientAge")).to_have_value("30")
            assert (
                page.locator('#completionForm [data-key="patient_name"]').count() == 0
            )
            assert page.locator('#completionForm [data-key="procedure"]').count() == 0
            page.locator('#completionForm [data-key="BAD_D"]').fill("1")
            page.locator('#completionForm [data-key="srax"]').select_option("NO")
            page.locator("#completeScreening").click()
        expect(page.locator("#results .NEGATIVE")).to_have_count(2)
        expect(page.locator("#output")).to_be_visible()
        expect(page.locator("#progressPercent")).to_have_text("100%")
        expect(page.locator("#progressBar")).to_have_attribute("value", "100")
        expect(page.locator("#pdfReport")).to_be_visible()
        pdf_url = f"/archive/cases/synthetic-case/revisions/synthetic-revision/report/pdf?locale={locale}"
        expect(page.locator("#openPDF")).to_have_attribute("href", pdf_url)
        expect(page.locator("#openPDF")).to_have_attribute("target", "_blank")
        expect(page.locator("#downloadPDF")).to_have_attribute("href", pdf_url)
        with page.expect_download() as download_info:
            page.locator("#downloadPDF").click()
        download = download_info.value
        assert download.suggested_filename == "CER-AI_Keratoconus_Screening.pdf"
        assert download.url.endswith(pdf_url)
        alternate = "en" if locale == "tr" else "tr"
        page.locator("#language").select_option(alternate)
        expect(page.locator("#downloadPDF")).to_have_attribute("href", pdf_url.replace(f"locale={locale}", f"locale={alternate}"))
        page.locator("#language").select_option(locale)
        assert b"patient_name" in uploads[0] and b"SYNTHETIC PATIENT" in uploads[0]
        assert b"patient_age" in uploads[0]
        assert len(uploads) == 1
        assert b"manifest_entered_sphere_D" in uploads[0]
        assert b"procedure" not in uploads[0] and b"intended" not in uploads[0]
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=f"/tmp/keratoconus-{locale}.png", full_page=True)
        page.locator("#OD_sphere").fill("-4")
        expect(page.locator("#output")).to_be_hidden()
        page.locator("#images").set_input_files(files[:4])
        page.locator("#analyze").click()
        expect(page.locator("#error")).not_to_be_empty()
        assert len(uploads) == 1
        assert errors == []
        browser.close()
