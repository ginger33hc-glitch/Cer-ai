"""Release provenance must identify the assessment, not the later renderer."""
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader
import pytest

import release_identity
import reports
import research_export
from test_step10_canonical_reports import _payload


@pytest.mark.parametrize("value", ("", "abcdef", "g" * 40, "<script>"))
def test_unknown_or_malformed_deployment_is_not_invented(monkeypatch, value):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", value)
    assert release_identity.deployment_sha() is None
    payload = _payload()
    assert payload["decision"]["deployment_sha"] is None
    assert payload["decision"]["eyes"][0]["report_payload"]["versions"]["deployment_sha"] is None


def test_archived_identity_survives_new_deployment_and_all_exports(monkeypatch):
    original_sha = "a123456789" * 4
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", original_sha.upper())
    payload = _payload()
    assert payload["decision"]["deployment_sha"] == original_sha
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "b" * 40)
    pdf_text = "".join(page.extract_text() for page in PdfReader(BytesIO(reports.build_pdf(payload))).pages)
    conclusion = PdfReader(BytesIO(reports.build_conclusion_pdf(payload)))
    assert len(conclusion.pages) == 1
    conclusion_text = conclusion.pages[0].extract_text()
    document = Document(BytesIO(reports.build_docx(payload)))
    word_text = " ".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    for text in (pdf_text, word_text, conclusion_text):
        assert original_sha in text
        assert "b" * 40 not in text
    row = research_export._row_for_eye(bytes(range(32)), {"case_id": "case", "revision_id": "revision"}, payload, payload["decision"]["eyes"][0])
    assert row["deployment_sha"] == original_sha
    assert row["software_version"] == "stage10-test"
    assert row["clinical_policy_version"] == payload["decision"]["policy_versions"]["clinical"]


def test_legacy_research_export_keeps_unknown_provenance_unknown(monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "b" * 40)
    row = research_export._row_for_eye(bytes(range(32)), {}, {"decision": {}}, {})
    assert row["deployment_sha"] is None
    assert row["software_version"] is None
    assert row["clinical_policy_version"] is None


def test_static_clinical_ui_matches_canonical_release():
    text = Path("static/index.html").read_text()
    assert f'v{release_identity.SOFTWARE_VERSION}</span>' in text
    assert f'Software v{release_identity.SOFTWARE_VERSION}</strong>' in text
