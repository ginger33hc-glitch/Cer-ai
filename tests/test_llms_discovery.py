"""Validate discovery links against the actual public routes, without clinical scoring."""
import re
from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import public_site
from public_education import TOPICS, TR_TOPICS


class PageLinks(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.canonicals = []
        self.ids = set()
        self.language = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if "id" in attrs:
            self.ids.add(attrs["id"])


@pytest.fixture
def client():
    core = SimpleNamespace(app=FastAPI())
    public_site.install(core)
    with TestClient(core.app, base_url="https://cer-ai.com") as client:
        yield client


def test_bilingual_screening_and_complete_learning_lists(client):
    response = client.get("/llms.txt")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    for path in ("/keratoconus-screening", "/tr/keratokonus-tarama",
                 "/learning/borderline-surgical-decisions",
                 "/tr/learning/borderline-surgical-decisions",
                 "/learning/faq", "/tr/learning/faq"):
        assert f"](https://cer-ai.com{path})" in text
    for prefix, topics in (("", TOPICS), ("/tr", TR_TOPICS)):
        for topic in topics:
            assert f"[{topic.title}](https://cer-ai.com{prefix}/learning/{topic.slug})" in text


def test_every_llms_link_resolves_to_public_canonical_page(client):
    urls = set(re.findall(r"\]\((https://[^)]+)\)", client.get("/llms.txt").text))
    assert urls
    for url in sorted(urls):
        parsed = urlsplit(url)
        assert parsed.netloc == "cer-ai.com"
        response = client.get(parsed.path, follow_redirects=False)
        assert response.status_code == 200, url
        assert response.headers["content-type"].startswith("text/html"), url
        page = PageLinks(response.text)
        assert page.canonicals == [f"https://cer-ai.com{parsed.path}"], url
        assert page.language == ("tr" if parsed.path.startswith("/tr/") else "en"), url
        if parsed.fragment:
            assert parsed.fragment in page.ids, url


def test_screening_boundaries_and_existing_module_hierarchy(client):
    text = client.get("/llms.txt").text
    for phrase in (
        "(1) Corneal Ectasia Risk Assessment",
        "(2) IOL Selection and Calculation",
        "The Toric Calculator is a capability within the second module, not a separate third module.",
        "A negative keratoconus screening result does not establish suitability for refractive surgery.",
        "Negatif keratokonus taraması, refraktif cerrahiye uygunluk anlamına gelmez.",
        "the Randleman/ERSS topography component is not the full ERSS surgical score",
        "planlanan refraktif işlemi ve işleme özgü doku güvenliğini",
        "Their results are not mathematically blended into one ectasia score.",
    ):
        assert phrase in text
