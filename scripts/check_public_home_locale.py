"""Public homepage EN/TR regression: Chromium desktop and WebKit iPhone emulation.

No clinical requests. Optional URL permits the same checks after deployment.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765/static/public-home.html')
    args = parser.parse_args()
    source = Path('static/public-i18n.js').read_text()
    translations = json.loads(source.split('const TR = ', 1)[1].split('\n  };', 1)[0] + '\n  }')
    prefixes = (
        'CER-AI: transparent assessment,',
        'CER-AI is not a black box:',
        'CER-AI brings together four literature-informed assessments:',
        'The IOL module brings spherical lens-power',
        'CER-AI is a web application,',
        'In clinical use tested by Dr.',
    )
    pairs = [(key, translations[key]) for prefix in prefixes
             for key in translations if key.startswith(prefix)]
    assert len(pairs) == len(prefixes)
    with sync_playwright() as p:
        for engine, options in ((p.chromium, {'viewport': {'width': 1440, 'height': 1000}}),
                                (p.webkit, p.devices['iPhone 13'])):
            browser = engine.launch()
            context = browser.new_context(**options)
            page = context.new_page()
            errors, scripts = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: scripts.append(request.url)
                    if '/public-i18n.js?' in request.url else None)
            page.goto(args.url, wait_until='networkidle')
            for language in ('en', 'tr', 'en', 'tr'):
                page.locator(f'#cerai-public-language button[data-lang="{language}"]').click()
                expect(page.locator('html')).to_have_attribute('lang', language)
                for en, tr in pairs:
                    expect(page.get_by_text(tr if language == 'tr' else en, exact=True)).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.reload(wait_until='networkidle')
            expect(page.locator('html')).to_have_attribute('lang', 'tr')
            for _, tr in pairs:
                expect(page.get_by_text(tr, exact=True)).to_be_visible()
            assert scripts and all(url.endswith('public-i18n.js?v=19') for url in scripts), scripts
            assert not errors, errors
            print(f'PASS {engine.name}: six new passages, EN/TR switching, stored TR reload, v19 requests, no overflow/JS errors')
            context.close()
            browser.close()


if __name__ == '__main__':
    main()
