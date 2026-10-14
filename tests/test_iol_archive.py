from io import BytesIO
from uuid import uuid4
from unittest.mock import patch

from pypdf import PdfReader

import case_catalog
from test_iol_report import sample_report
from test_named_user_ui import make_client


def setup_archive(role='DOCTOR', runtime=None):
    client, core = make_client(role)
    if runtime is not None:
        core._cerai_case_archive_runtime = runtime
    case_catalog.install(core, core._cerai_case_archive_runtime)
    client.cookies.set('cer_ai_session', 'valid')
    return client, core


def test_iol_pdf_is_indexed_retrievable_bilingual_and_idempotent():
    client, core = setup_archive()
    body = sample_report().model_dump(mode='json')
    body['assessment_request_id'] = str(uuid4())
    response = client.post('/iol/report/pdf', json=body)
    assert response.status_code == 200
    assert response.headers['X-CERAI-Archive-Status'] == 'ARCHIVED'
    again = client.post('/iol/report/pdf', json={**body, 'locale':'en'})
    assert again.status_code == 200
    entries = client.post('/archive/search', json={'patient_name':body['patient_name']}).json()['results']
    assert len(entries) == 1 and entries[0]['module'] == 'IOL'
    entry = entries[0]
    base = f"/archive/cases/{entry['case_id']}/revisions/{entry['revision_id']}"
    tr_pdf = client.get(base+'/report/pdf?locale=tr')
    assert tr_pdf.content == response.content
    assert client.get(base+'/report/pdf?locale=en').content == again.content
    assert client.get(base+'/report/docx').status_code == 404
    assert body['patient_name'] in PdfReader(BytesIO(tr_pdf.content)).pages[0].extract_text()
    owner, _ = setup_archive('OWNER', core._cerai_case_archive_runtime)
    masked = owner.get(base+'/report/pdf?locale=tr')
    assert masked.status_code == 200
    text = PdfReader(BytesIO(masked.content)).pages[0].extract_text()
    assert body['patient_name'] not in text and 'Masked for owner' in text


def test_failed_iol_archive_blocks_ready_pdf_and_can_retry():
    client, core = setup_archive()
    body = sample_report().model_dump(mode='json')
    body['assessment_request_id'] = str(uuid4())
    with patch.object(core._cerai_case_archive_runtime.archive.store, 'put', side_effect=OSError('unavailable')):
        response = client.post('/iol/report/pdf', json=body)
    assert response.status_code == 503
    assert client.post('/iol/report/pdf', json=body).status_code == 200
    assert len(client.post('/archive/search', json={}).json()['results']) == 1


def test_iol_index_failure_retry_recovers_saved_pdfs_without_duplicates():
    client, core = setup_archive()
    body = sample_report().model_dump(mode='json')
    body['assessment_request_id'] = str(uuid4())
    with patch('case_catalog.write_entry', side_effect=OSError('index unavailable')):
        assert client.post('/iol/report/pdf', json=body).status_code == 503
    response = client.post('/iol/report/pdf', json=body)
    assert response.status_code == 200
    entries = client.post('/archive/search', json={}).json()['results']
    assert len(entries) == 1
    archive = core._cerai_case_archive_runtime.archive
    for locale in ['tr', 'en']:
        assert archive.find_report(entries[0]['case_id'], entries[0]['revision_id'], locale, 'pdf') is not None
