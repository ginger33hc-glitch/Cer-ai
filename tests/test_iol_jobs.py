import asyncio
import hashlib
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import operational_security
import user_access
from iol_module.jobs import install, CHUNK_BYTES


def manifest(raw=b'synthetic original image', request_id='assessment-1'):
    return {'request_id':request_id,'patient_name':'Synthetic QA', 'files':[
        {'name':f'source-{i}.jpg','type':'image/jpeg','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for i in range(3)]}


@pytest.fixture
def setup():
    app = FastAPI()
    calls = []
    async def process(payloads, principal, request_id, patient_name, progress):
        calls.append((payloads,principal.user_id,request_id,patient_name))
        await asyncio.sleep(.05)
        progress('ARCHIVING',len(payloads))
        return {'identity':{'patient_name':patient_name},'sources':[name for _,name in payloads]}
    def auth(request):
        owner = request.cookies.get('cer_ai_session')
        return user_access.Principal(owner,owner,owner,'DOCTOR') if owner else None
    core=SimpleNamespace(app=app,_cerai_named_users_enabled=True,_cerai_authenticate_request=auth,
                         _cerai_bind_principal=user_access.bind_current_principal,_cerai_reset_principal=user_access.reset_current_principal)
    install(core,process)
    operational_security.install(core)
    with TestClient(app,base_url='https://testserver') as client:
        client.cookies.set('cer_ai_session','doctor-1')
        yield client,calls


def upload_all(client, base, raw):
    for index in range(3):
        for offset in range(0,len(raw),CHUNK_BYTES):
            chunk=raw[offset:offset+CHUNK_BYTES]
            url=f'{base}/images/{index}?offset={offset}'
            response=client.put(url,content=chunk)
            assert response.status_code==200,response.text
            # A lost response is retried without appending the bytes twice.
            assert client.put(url,content=chunk).json()==response.json()


def test_detached_processing_idempotent_upload_start_and_retrieval(setup):
    client,calls=setup
    raw=b'x'*(CHUNK_BYTES+13)
    body=manifest(raw)
    created=client.post('/iol/jobs',json=body)
    assert created.status_code==202
    job=created.json(); base='/iol/jobs/'+job['job_id']
    assert client.post('/iol/jobs',json=body).json()['job_id']==job['job_id']
    assert client.post(base+'/start').status_code==409
    upload_all(client,base,raw)
    started=client.post(base+'/start')
    assert started.json()['status']=='READING'
    assert client.post(base+'/start').status_code==202
    # No request remains open while the worker finishes.
    import time
    time.sleep(.15)
    result=client.get(base)
    assert result.json()['status']=='COMPLETED'
    assert 'no-store' in result.headers['cache-control']
    assert len(calls)==1
    assert calls[0]==([(raw,f'source-{i}.jpg') for i in range(3)],'doctor-1','assessment-1','Synthetic QA')
    assert client.post('/iol/jobs',json=body).json()['result']==result.json()['result']


def test_ownership_auth_integrity_and_invalid_chunks(setup):
    client,_=setup
    raw=b'original'
    base='/iol/jobs/'+client.post('/iol/jobs',json=manifest(raw)).json()['job_id']
    assert client.put(base+'/images/0?offset=1',content=raw).status_code==409
    assert client.put(base+'/images/0',content=b'x'*(CHUNK_BYTES+1)).status_code==413
    upload_all(client,base,b'changed!')
    assert client.post(base+'/start').status_code==409
    assert client.put(base+'/images/0',content=raw).status_code==409
    client.cookies.set('cer_ai_session','doctor-2')
    for method,path in [('get',base),('post',base+'/start'),('put',base+'/images/0')]:
        assert getattr(client,method)(path).status_code==403
    client.cookies.clear()
    assert client.get(base).status_code==401
    assert client.post('/iol/jobs',json=manifest()).status_code==401


def test_new_selection_replaces_only_unfinished_upload(setup):
    client,_=setup
    first=client.post('/iol/jobs',json=manifest()).json()['job_id']
    second=client.post('/iol/jobs',json=manifest(request_id='second'))
    assert second.status_code==202
    assert client.get('/iol/jobs/'+first).status_code==410
    base='/iol/jobs/'+second.json()['job_id']
    upload_all(client,base,b'synthetic original image')
    client.post(base+'/start')
    assert client.post('/iol/jobs',json=manifest(request_id='third')).status_code==429


def test_failed_job_preserves_actionable_error_and_does_not_restart(monkeypatch):
    app=FastAPI(); calls=[]
    async def fail(*args):
        calls.append(1)
        raise HTTPException(422,'Source eye identity does not match.')
    monkeypatch.setattr(user_access,'require_current_principal',lambda:SimpleNamespace(user_id='doctor'))
    install(SimpleNamespace(app=app),fail)
    with TestClient(app) as client:
        base='/iol/jobs/'+client.post('/iol/jobs',json=manifest()).json()['job_id']
        upload_all(client,base,b'synthetic original image')
        client.post(base+'/start')
        import time
        time.sleep(.02)
        result=client.get(base).json()
        assert result['status']=='FAILED' and result['http_status']==422
        assert result['detail']=='Source eye identity does not match.'
        client.post(base+'/start')
        assert len(calls)==1


def test_job_uses_shared_source_validation_archive_and_single_credit(monkeypatch):
    from unittest.mock import Mock
    from test_iol_archive import setup_archive
    from iol_module import web
    import time
    client,core=setup_archive()
    core._cerai_assert_demo_credit=Mock()
    core._cerai_consume_demo_credit=Mock()
    monkeypatch.setattr(web,'extract_image',lambda core,raw,name:{'original':raw.decode()})
    monkeypatch.setattr(web,'validate_source_bundle',lambda results,surgeon_patient_name:{'patient_name':surgeon_patient_name,'eye':'OD'})
    with client:
        base='/iol/jobs/'+client.post('/iol/jobs',json=manifest()).json()['job_id']
        upload_all(client,base,b'synthetic original image')
        client.post(base+'/start')
        for _ in range(100):
            result=client.get(base).json()
            if result['status'] in {'FAILED','COMPLETED'}: break
            time.sleep(.01)
        assert result['status']=='COMPLETED',result
        assert result['result']['source_archive']['count']==3
        archive=core._cerai_case_archive_runtime.archive
        refs=archive.list_sources(result['result']['source_archive']['case_id'])
        assert all(archive.get_bytes(ref.artifact)==b'synthetic original image' for ref in refs)
        client.post(base+'/start')
        core._cerai_consume_demo_credit.assert_called_once_with('doctor-1','assessment-1','IOL')
