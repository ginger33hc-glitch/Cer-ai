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


@pytest.mark.parametrize("locale,width", [("en", 1280), ("tr", 390)])
def test_screening_browser(locale, width):
    extracted, refs = fixture_case()
    result = evaluate_extracted(extracted, refs)
    result["archive"] = None
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
        context = browser.new_context(viewport={"width": width, "height": 900})
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
            elif path == "/keratoconus/analyze":
                uploads.append(request.request.post_data_buffer)
                request.fulfill(json=result)
            else:
                request.fulfill(status=404, body="")

        page.route("**/*", route)
        page.goto("http://cerai.test/keratoconus")
        expect(page.locator("h1")).to_have_text(
            "Keratokonus Tarama" if locale == "tr" else "Keratoconus Screening"
        )
        assert page.locator("input[type=number]").count() == 6
        assert (
            page.locator("select").count() == 1
        )  # Language only; no procedure selector.
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
        expect(page.locator("#results .NEGATIVE")).to_have_count(2)
        expect(page.locator("#output")).to_be_visible()
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
