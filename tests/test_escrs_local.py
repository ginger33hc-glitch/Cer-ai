"""Local session ownership, bounded capacity, input validation and provider routing."""
from types import SimpleNamespace
from time import monotonic
from unittest.mock import patch
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from iol_module import escrs_local as local
from iol_module.escrs_cloud import CloudTransfer
from test_escrs_cloud import case


@pytest.fixture
def record():
    item = local.Session('doctor')
    item.ready.set_result({})
    item.expires = monotonic()+900
    local._sessions[item.view_id] = item
    yield item
    item.stop.set()
    local._sessions.clear()


def test_ownership_expiry_and_capacity(record, monkeypatch):
    assert local._owned(record.view_id,'doctor') is record
    with pytest.raises(HTTPException) as exc:
        local._owned(record.view_id,'other')
    assert exc.value.status_code == 403
    monkeypatch.setattr(local,'executable',lambda:'/usr/bin/chromium')
    with pytest.raises(HTTPException) as exc:
        local.create_local_transfer(CloudTransfer.model_validate(case()),'doctor')
    assert exc.value.status_code == 429
    record.expires = monotonic()-1
    with pytest.raises(HTTPException) as exc:
        local._owned(record.view_id,'doctor')
    assert exc.value.status_code == 410


@pytest.mark.parametrize('payload',[
    {'kind':'click','x':-1,'y':0}, {'kind':'click','x':True,'y':0},
    {'kind':'click','x':float('nan'),'y':0}, {'kind':'scroll','delta':9999},
    {'kind':'key','key':'Control+L'}, {'kind':'text','text':'x'*501},
    {'kind':'frame'}, {'kind':'pdf'}, {'kind':'navigate','url':'http://localhost'},
])
def test_invalid_commands(payload):
    with pytest.raises(HTTPException): local._input(payload)


def test_frame_pdf_and_controls_require_session_owner(record):
    core=SimpleNamespace(app=FastAPI())
    local.install(core)
    base='/iol/escrs-local/'+record.view_id
    with TestClient(core.app) as client:
        for identity, code in [(HTTPException(401,'Sign in'),401),(SimpleNamespace(user_id='other'),403)]:
            kwargs={'side_effect':identity} if isinstance(identity,Exception) else {'return_value':identity}
            with patch('user_access.require_current_principal',**kwargs):
                for path in ('','/status','/frame','/pdf'):
                    assert client.get(base+path).status_code == code
                for path in ('/input','/close'):
                    assert client.post(base+path,json={'kind':'text','text':'1'}).status_code == code
        with patch('user_access.require_current_principal',return_value=SimpleNamespace(user_id='doctor')):
            assert client.get(base).headers['cache-control']=='no-store'
            assert client.get(base+'/status').json()['seconds_remaining'] > 120
            assert client.post(base+'/close',json={}).status_code==200


def test_navigation_away_blocks_capture_and_pointer():
    cdp=SimpleNamespace(call=lambda *a,**kw:{'result':{'value':'other.example'}})
    for command in ({'kind':'frame'}, {'kind':'pdf'}, {'kind':'click','x':0,'y':0}):
        with pytest.raises(HTTPException): local._dispatch(cdp,'page',command)


def test_local_provider_without_vendor_keys(monkeypatch):
    from iol_module.web import install
    monkeypatch.setenv('CERAI_ESCRS_PROVIDER','local')
    monkeypatch.delenv('BROWSERLESS_TOKEN',raising=False)
    monkeypatch.delenv('BROWSERBASE_API_KEY',raising=False)
    monkeypatch.setattr(local,'executable',lambda:'/usr/bin/chromium')
    events=[]
    core=SimpleNamespace(app=FastAPI(),_cerai_audit_event=lambda e,**kw:events.append((e,kw)) or {'saved':True})
    install(core)
    body=case();body.update(provider='local',consent_version='ESCRS-CLOUD-2026-10-17-V2')
    with TestClient(core.app) as client, patch('user_access.require_current_principal',return_value=SimpleNamespace(user_id='doctor',display_name='Doctor')), patch.object(local,'create_local_transfer',return_value={'verified':True}) as transfer:
        assert client.get('/iol/escrs-cloud-config').json()['enabled'] is True
        assert client.post('/iol/escrs-cloud-transfer',json=body).status_code == 200
        assert transfer.call_args.args[1]=='doctor'
        assert events[0][1]['details']['recipients']==['ESCRS IOL Calculator']


def test_local_paths_bind_named_user_in_real_middleware(record):
    import operational_security
    import user_access
    principal=SimpleNamespace(user_id='doctor')
    core=SimpleNamespace(app=FastAPI(),_cerai_named_users_enabled=True,
        _cerai_authenticate_request=lambda request: principal if request.cookies.get('test')=='signed-in' else None,
        _cerai_bind_principal=user_access.bind_current_principal,
        _cerai_reset_principal=user_access.reset_current_principal)
    local.install(core)
    operational_security.install(core)
    with TestClient(core.app) as client:
        base='/iol/escrs-local/'+record.view_id
        assert client.get(base+'/status').status_code==401
        client.cookies.set('test','signed-in')
        response=client.get(base+'/status')
        assert response.status_code==200
        assert response.headers['cache-control']=='no-store'
        assert client.post(base+'/close',json={}).status_code==200
