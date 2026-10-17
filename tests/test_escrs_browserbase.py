"""Provider handoff, isolation, cleanup and mobile input regression without patient data."""
import json
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from iol_module import escrs_browserbase as bb
from iol_module.escrs_cloud import CloudTransfer
from test_escrs_cloud import case


class Socket:
    def __init__(self, wrong=False):
        self.command = None
        self.commands = []
        self.wrong = wrong

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def send(self, message):
        self.command = json.loads(message)
        self.commands.append(self.command)

    def recv(self, timeout):
        item = self.command
        method = item['method']
        if method == 'Target.createTarget': result = {'targetId':'page'}
        elif method == 'Target.attachToTarget': result = {'sessionId':'cdp-page'}
        elif method == 'Runtime.evaluate':
            expression = item['params']['expression']
            if 'CeraiEscrsAdapter.run' in expression:
                value = {'OD':'Wrong' if self.wrong else 'Clareon PanOptix Toric CNWTT2-6','OS':'DEN00V'}
            elif 'editable:' in expression: value = {'host':'iolcalculator.escrs.org','editable':True}
            else: value = True
            result = {'result':{'value':value}}
        else: result = {}
        return json.dumps({'id':item['id'],'result':result})


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv('BROWSERBASE_API_KEY','private-provider-key')
    monkeypatch.setenv('BROWSERBASE_PROJECT_ID',str(uuid4()))
    bb._sessions.clear()
    released = Event()
    requests = []
    socket = Socket()
    session_id = str(uuid4())
    def api(path='', body=None):
        requests.append((path,body))
        if not path:
            return {'id':session_id,'connectUrl':'wss://connect.browserbase.com?apiKey=private-provider-key'}
        if path.endswith('/debug'):
            return {'pages':[{'url':'https://iolcalculator.escrs.org/', 'debuggerFullscreenUrl':'https://www.browserbase.com/devtools-internal-fully?sessionId='+session_id}]}
        released.set()
        return {}
    monkeypatch.setattr(bb,'_api',api)
    monkeypatch.setattr(bb,'connect',lambda *a,**kw:socket)
    yield SimpleNamespace(released=released,requests=requests,socket=socket)
    for record in list(bb._sessions.values()): record.stop.set()
    if bb._sessions: released.wait(2)


def test_free_compatible_connection_holds_five_minutes_and_releases(provider):
    result = bb.create_browserbase_transfer(CloudTransfer.model_validate(case()),'doctor')
    assert result['viewer_limit_seconds'] == 300
    assert result['escrs_url'].startswith('/iol/escrs-session/')
    assert 'private-provider-key' not in json.dumps(result)
    options = provider.requests[0][1]
    assert options['timeout'] == 425 and options['keepAlive'] is False
    assert options['proxies'] is False
    assert options['browserSettings']['recordSession'] is False
    assert options['browserSettings']['logSession'] is False
    record=bb._sessions[result['escrs_url'].rsplit('/',1)[1]]
    with pytest.raises(HTTPException) as caught:
        bb.create_browserbase_transfer(CloudTransfer.model_validate(case()),'doctor')
    assert caught.value.status_code == 429
    record.stop.set()
    assert provider.released.wait(2)
    assert provider.requests[-1][1]['status'] == 'REQUEST_RELEASE'


def test_mismatched_readback_fails_closed_and_releases(provider):
    provider.socket.wrong=True
    with pytest.raises(HTTPException) as caught:
        bb.create_browserbase_transfer(CloudTransfer.model_validate(case()),'doctor')
    assert caught.value.status_code == 502
    assert 'private-provider-key' not in caught.value.detail
    assert provider.released.wait(2)


def test_viewer_and_keyboard_are_authenticated_and_owned(provider):
    result=bb.create_browserbase_transfer(CloudTransfer.model_validate(case()),'doctor')
    base=result['escrs_url']
    core=SimpleNamespace(app=FastAPI())
    bb.install(core)
    with TestClient(core.app) as client:
        with patch('user_access.require_current_principal',side_effect=HTTPException(401,'Sign in')):
            assert client.get(base).status_code == 401
            assert client.post(base+'/input',json={'kind':'text','text':'1'}).status_code == 401
        with patch('user_access.require_current_principal',return_value=SimpleNamespace(user_id='other')):
            for path in ('','/status'):
                assert client.get(base+path).status_code == 403
            assert client.post(base+'/close').status_code == 403
            assert client.post(base+'/input',json={'kind':'text','text':'1'}).status_code == 403
        with patch('user_access.require_current_principal',return_value=SimpleNamespace(user_id='doctor')):
            assert client.get(base).status_code == 200
            assert 'private-provider-key' not in client.get(base+'/status').text
            assert client.post(base+'/input',json={'kind':'key','key':'Control+L'}).status_code == 422
            assert client.post(base+'/input',json={'kind':'text','text':'x'*501}).status_code == 422
            assert client.post(base+'/input',json={'kind':'text','text':'0.25'}).status_code == 200
            typed=[c for c in provider.socket.commands if c['method']=='Input.insertText']
            assert typed[-1]['params']['text'] == '0.25'
            assert client.post(base+'/close').status_code == 200
    assert provider.released.wait(2)


def test_non_provider_urls_and_non_escrs_keyboard_targets_rejected():
    for value in ('http://www.browserbase.com','https://browserbase.com.attacker.example','https://user:pass@www.browserbase.com'):
        with pytest.raises(ValueError): bb._provider_url(value)
    cdp=SimpleNamespace(call=lambda *a,**kw:{'result':{'value':{'host':'other.example','editable':True}}})
    with pytest.raises(HTTPException) as caught:
        bb._command(cdp,'page',{'kind':'text','text':'not sent'})
    assert caught.value.status_code == 409


def test_provider_selection_requires_new_specific_disclosure(monkeypatch):
    from iol_module.web import install
    monkeypatch.setenv('CERAI_ESCRS_PROVIDER','browserbase')
    monkeypatch.setenv('BROWSERBASE_API_KEY','private-provider-key')
    events=[]
    core=SimpleNamespace(app=FastAPI(),_cerai_audit_event=lambda e,**kw: events.append((e,kw)) or {'saved':True})
    install(core)
    body=case()
    with TestClient(core.app) as client, patch('user_access.require_current_principal',return_value=SimpleNamespace(user_id='doctor',display_name='Doctor')), patch.object(bb,'create_browserbase_transfer',return_value={'verified':True}) as transfer:
        assert client.get('/iol/escrs-cloud-config').json()['provider'] == 'browserbase'
        assert client.post('/iol/escrs-cloud-transfer',json=body).status_code == 409
        transfer.assert_not_called()
        assert not events
        body.update(provider='browserbase',consent_version='ESCRS-CLOUD-2026-10-17-V2')
        assert client.post('/iol/escrs-cloud-transfer',json=body).status_code == 200
        assert events[0][1]['details']['recipients'] == ['Browserbase','ESCRS IOL Calculator']
        assert 'CT' not in json.dumps(events[0][1]['details'])
