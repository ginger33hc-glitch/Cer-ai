"""Synthetic UI only: no patient data or external services."""
import json
from pathlib import Path
from urllib.parse import urlparse
import pytest
from test_refractive_completion_browser import browser  # shared Chromium fixture

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('locale', ['en', 'tr'])
def test_smile_device_defaults_edit_invalidation_and_submission(browser, locale):
    context = browser.new_context()
    context.add_init_script("localStorage.setItem('cerai-language'," + json.dumps(locale) + ");")
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    def route(request):
        path = urlparse(request.request.url).path
        file = ROOT / ('static/index.html' if path == '/app' else path.lstrip('/'))
        if file.is_file():
            request.fulfill(path=str(file))
        else:
            request.fulfill(status=204)
    page.route('**/*', route)
    try:
        page.goto('https://synthetic.test/app')
        page.locator('#od_procedure').select_option('SMILE')
        assert page.locator('#od_smile_cap').input_value() == '120'
        assert page.locator('#od_optical').input_value() == '6.5'
        assert page.locator('#od_smile_platform').input_value() == 'ZEISS_VISUMAX_500'
        page.locator('#od_lenticule').fill('70')
        plan = page.evaluate("plan('od')")
        assert plan['max_lenticule_thickness_um'] == 70
        assert plan['lenticule_source'] == 'SURGEON_ENTERED_VISUMAX_MAXIMUM'
        page.locator('#os_lenticule').fill('80')
        page.locator('#od_smile_platform').select_option('ZEISS_VISUMAX_800')
        assert page.locator('#od_lenticule').input_value() == ''
        assert page.locator('#os_lenticule').input_value() == '80'
        page.locator('#od_lenticule').fill('65')
        page.locator('#od_smile_cap').select_option('130')
        assert page.locator('#od_lenticule').input_value() == ''
        note = page.locator('#od_lenticule').locator('..').inner_text()
        assert ('MAKSİMUM' if locale == 'tr' else 'MAXIMUM') in note
        assert not errors
    finally:
        context.close()
