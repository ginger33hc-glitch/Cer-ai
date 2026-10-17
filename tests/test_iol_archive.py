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


def test_source_upload_is_encrypted_idempotent_and_linked_to_versioned_report(monkeypatch):
    import json
    from iol_module.provenance import IOL_POLICY_VERSION
    from release_identity import SOFTWARE_VERSION
    monkeypatch.setenv('RAILWAY_GIT_COMMIT_SHA', 'a' * 40)
    client, core = setup_archive()
    body = sample_report().model_dump(mode='json')
    request_id = str(uuid4())
    body['assessment_request_id'] = request_id
    files = [('images', (f'image-{i}.png', f'synthetic-source-{i}'.encode(), 'image/png')) for i in range(3)]
    with patch('iol_module.web.extract_image', return_value={}), patch(
        'iol_module.web.validate_source_bundle', return_value={'patient_name': body['patient_name'], 'eye':'OD'}
    ):
        upload = client.post('/iol/extract', files=files, data={
            'assessment_request_id':request_id, 'patient_name':body['patient_name']})
        assert upload.status_code == 200
        info = upload.json()['source_archive']
        assert info['count'] == 3
        again = client.post('/iol/extract', files=files, data={
            'assessment_request_id':request_id, 'patient_name':body['patient_name']})
        assert again.status_code == 200
        changed = list(files)
        changed[0] = ('images', ('changed.png', b'different-source', 'image/png'))
        assert client.post('/iol/extract', files=changed, data={
            'assessment_request_id':request_id, 'patient_name':body['patient_name']}).status_code == 409
    archive = core._cerai_case_archive_runtime.archive
    refs = archive.list_sources(info['case_id'])
    assert len(refs) == 3
    assert archive.get_bytes(refs[0].artifact) == b'synthetic-source-0'
    assert b'synthetic-source-0' not in archive.store.get(refs[0].artifact.key).data
    response = client.post('/iol/report/pdf', json=body)
    assert response.status_code == 200
    assert response.headers['X-CERAI-Case-ID'] == info['case_id']
    assessment_key = next(key for key in archive.store.list(f"cases/{info['case_id']}/revisions/") if 'assessment-json' in key)
    saved = json.loads(archive.get_bytes(assessment_key))
    assert saved['versions'] == {'software':SOFTWARE_VERSION, 'clinical_policy':IOL_POLICY_VERSION, 'deployment_sha':'a'*40}
    assert len(saved['source_artifacts']) == 3
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
    assert SOFTWARE_VERSION in text and IOL_POLICY_VERSION in text and 'a'*40 in text
    other, _ = setup_archive('OWNER', core._cerai_case_archive_runtime)
    base = f"/archive/cases/{info['case_id']}/revisions/{response.headers['X-CERAI-Revision-ID']}"
    assert client.get(base + '/sources/1/download').content == b'synthetic-source-0'
    # Source access continues to use the archive's existing role-scoped policy.
    assert other.get(base + '/sources/1/download').status_code == 403


def test_failed_source_archive_does_not_release_extraction():
    client, core = setup_archive()
    files = [('images', (f'{i}.png', b'source', 'image/png')) for i in range(3)]
    with patch('iol_module.web.extract_image', return_value={}), patch(
        'iol_module.web.validate_source_bundle', return_value={'eye':'OD'}
    ), patch.object(core._cerai_case_archive_runtime.archive.store, 'put', side_effect=OSError('unavailable')):
        response = client.post('/iol/extract', files=files, data={
            'assessment_request_id':str(uuid4()), 'patient_name':'Synthetic case'})
    assert response.status_code == 503


def test_legacy_snapshot_is_not_relabelled_with_current_release():
    from iol_module.archive import build_archived_iol_pdf
    snapshot = {'iol_report':sample_report().model_dump(mode='json'),
                'patient':{'reviewer':'Doctor','report_date':'2026-01-01'}}
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(build_archived_iol_pdf(snapshot))).pages)
    assert 'Software: UNKNOWN' in text and 'Commit: UNKNOWN' in text
