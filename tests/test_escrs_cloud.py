import io
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from experiments.escrs_cloud.server import synthetic_case
from iol_module.escrs_cloud import CloudTransfer, _leases, build_query, create_cloud_transfer, model_names


def case():
    payload = synthetic_case()
    payload["initials"] = "CT"
    payload["terms_accepted"] = True
    payload["data_transfer_accepted"] = True
    payload["consent_version"] = "ESCRS-BROWSERLESS-2026-10-17"
    payload["eyes"]["OD"]["lens_id"] = "clareon-panoptix-toric-cnwtt3"
    payload["eyes"]["OS"]["lens_id"] = "tecnis-puresee-den00v"
    return payload


@pytest.fixture(autouse=True)
def clean_leases(monkeypatch):
    _leases.clear()
    monkeypatch.delenv("BROWSERLESS_SESSION_SECONDS", raising=False)
    monkeypatch.delenv("CERAI_ESCRS_PROVIDER", raising=False)
    monkeypatch.setenv("BROWSERLESS_TOKEN", "test-secret-do-not-return")
    monkeypatch.setenv("BROWSERLESS_HOST", "production-sfo.browserless.io")
    yield
    _leases.clear()


def test_cloud_input_rejects_wrong_model_manufacturer_mode_and_consent():
    for change in (
        lambda p: p.update(terms_accepted=False),
        lambda p: p.update(data_transfer_accepted=False),
        lambda p: p.pop("data_transfer_accepted"),
        lambda p: p.update(consent_version="old"),
        lambda p: p["eyes"]["OD"].update(toric=False),
        lambda p: p["eyes"]["OS"].update(lens_matches=["DRN00V"]),
        lambda p: p["eyes"]["OD"].update(manufacturer_matches=["Other"]),
        lambda p: p["eyes"]["OD"].update(k1_axis_deg=16),
        lambda p: p.update(initials="Full Patient Name"),
        lambda p: p.update(age=True),
    ):
        payload = case()
        change(payload)
        with pytest.raises(ValidationError):
            CloudTransfer.model_validate(payload)


def test_bql_quotes_payload_and_uses_canonical_adapter_without_automatic_calculation():
    payload = case()
    payload["surgeon"] = 'Doctor "Test" \\ new'
    query = build_query(CloudTransfer.model_validate(payload))
    assert "CeraiEscrsAdapter.run" in query
    assert "mousedown" in query
    assert "detached:true" in query and "reconnect(timeout:90000)" in query
    assert "test-secret" not in query
    assert "solveCaptcha" not in query
    assert "click(selector:\"[...document.querySelectorAll" in query
    assert model_names()["tecnis-puresee-den00v"] == "DEN00V"


def upstream(selected=None, errors=None, url=None):
    return io.BytesIO(json.dumps({"data": {
        "verify": {"value": json.dumps(selected or {"OD": "Clareon PanOptix Toric CNWTT2-6", "OS": "DEN00V"})},
        "liveURL": {"liveURL": url or "https://production-sfo.browserless.io/e/test/live/index.html?i=viewer"},
        "reconnect": {"browserWSEndpoint": "never-expose-this"},
    }, **({"errors": errors} if errors else {})}).encode())


def test_handoff_returns_only_verified_viewer_and_bounds_active_sessions():
    with patch("iol_module.escrs_cloud.urlopen", return_value=upstream()) as fetch:
        result = create_cloud_transfer(CloudTransfer.model_validate(case()), "doctor")
        assert result["verified"] is True
        assert "never-expose" not in json.dumps(result)
        assert "test-secret" not in json.dumps(result)
        assert "test-secret" not in fetch.call_args.args[0].data.decode()
        with pytest.raises(HTTPException) as caught:
            create_cloud_transfer(CloudTransfer.model_validate(case()), "doctor")
        assert caught.value.status_code == 429


@pytest.mark.parametrize("reply", [
    lambda: upstream(selected={"OD": "Wrong IOL", "OS": "DEN00V"}),
    lambda: upstream(errors=[{"message": "verification failed"}]),
    lambda: upstream(url="https://other.example/e/test/live/index.html"),
])
def test_failed_readback_or_wrong_viewer_cannot_be_opened(reply):
    with patch("iol_module.escrs_cloud.urlopen", return_value=reply()):
        with pytest.raises(HTTPException) as caught:
            create_cloud_transfer(CloudTransfer.model_validate(case()), "doctor")
    assert caught.value.status_code == 502
    assert not _leases


def test_upstream_error_does_not_echo_secret_url():
    error = HTTPError("https://example/?token=test-secret-do-not-return", 401, "Unauthorized", {}, None)
    with patch("iol_module.escrs_cloud.urlopen", side_effect=error):
        with pytest.raises(HTTPException) as caught:
            create_cloud_transfer(CloudTransfer.model_validate(case()), "doctor")
    assert "test-secret" not in caught.value.detail


def test_cloud_routes_require_login_and_use_server_doctor_identity(caplog):
    from iol_module.web import install
    import operational_security
    events = []
    core = SimpleNamespace(app=FastAPI(), _cerai_audit_event=lambda event, **kw: events.append((event,kw)) or {"recorded": True})
    install(core)
    with TestClient(core.app) as client:
        assert client.get("/iol/escrs-cloud-config").status_code == 401
        assert client.post("/iol/escrs-cloud-transfer", json=case()).status_code == 401
        with patch("user_access.require_current_principal", return_value=SimpleNamespace(user_id="doctor", display_name="Signed-in Surgeon")), patch("iol_module.escrs_cloud.create_cloud_transfer", return_value={"verified": True}) as transfer:
            stale = case()
            stale.pop("data_transfer_accepted")
            stale.pop("consent_version")
            assert client.post("/iol/escrs-cloud-transfer", json=stale).status_code == 422
            transfer.assert_not_called()
            assert "data_transfer_accepted" in caplog.text and "consent_version" in caplog.text
            assert "Signed-in Surgeon" not in caplog.text and "test-secret" not in caplog.text
            response = client.post("/iol/escrs-cloud-transfer", json=case())
            assert response.status_code == 200
            assert transfer.call_args.args[0].surgeon == "Signed-in Surgeon"
            assert [e[0] for e in events] == ["ESCRS_TRANSFER_CONSENT", "ESCRS_TRANSFER_OUTCOME"]
            evidence = json.dumps([e[1]["details"] for e in events])
            for value in ("CT", "Signed-in Surgeon", "liveURL", "test-secret", "axial_length_mm"):
                assert value not in evidence
            events.clear()
            transfer.side_effect = HTTPException(502, "Private upstream details")
            assert client.post("/iol/escrs-cloud-transfer", json=case()).status_code == 502
            assert events[-1][1]["details"] == {"status":"FAILED", "http_status":502}
            assert "Private upstream" not in str(events)
            core._cerai_audit_event = lambda *a, **kw: None
            transfer.reset_mock()
            assert client.post("/iol/escrs-cloud-transfer", json=case()).status_code == 503
            transfer.assert_not_called()
            del core._cerai_audit_event
            transfer.reset_mock()
            assert client.post("/iol/escrs-cloud-transfer", json=case()).status_code == 503
            transfer.assert_not_called()
    assert "/iol/escrs-cloud-transfer" in operational_security.PROTECTED_PATHS


def test_mobile_web_handoff_preserves_case_after_verified_consent():
    if not shutil.which("node"):
        pytest.skip("Node unavailable")
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const names=JSON.parse(fs.readFileSync('static/escrs-models.json','utf8'));
let provider="browserless",consent=true,fail=false,validation=null,destination,navigations=0,posts=0;
const ctx={URL,window:{location:{origin:"https://cer-ai.com",assign:u=>{destination=u;navigations++;}},confirm:message=>{assert(message.includes(provider==="browserbase"?"Browserbase":"Browserless"));assert(message.includes("initials"));assert(message.includes("ESCRS calculator terms"));return consent;},open:()=>{throw new Error("Mobile transfer must not open a popup");}},fetch:async(url,options)=>{
 if(url==='/auth/me')return {ok:true,json:async()=>({user:{display_name:'Signed-in Doctor'}})};
 if(url==='/iol/escrs-cloud-config')return {ok:true,json:async()=>({enabled:true,models:names,provider})};
 assert.equal(url,'/iol/escrs-cloud-transfer');posts++;const p=JSON.parse(options.body);
 assert.equal(p.terms_accepted,true);assert.equal(p.data_transfer_accepted,true);assert.equal(p.consent_version,"ESCRS-CLOUD-2026-10-17-V2");assert.equal(p.provider,provider);assert.equal(p.surgeon,'Signed-in Doctor');
 assert.equal(p.eyes.OD.toric,true);assert.equal(p.eyes.OS.toric,false);
 assert.equal(p.initials,'CT');assert(!JSON.stringify(p).includes('Case Test'));
 return {ok:!fail&&!validation,status:validation?422:fail?502:200,json:async()=>validation?{detail:[{loc:[validation],input:"private-input"}]}:fail?{detail:'Verification failed'}:{escrs_url:provider==='browserbase'?'/iol/escrs-session/'+'a'.repeat(32):'https://production-sfo.browserless.io/e/x/live/index.html?i=viewer'}};
}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/iol-escrs-assistant.js','utf8'),ctx);
const eye=side=>({eye:side,biological_sex:'Female',axial_length_mm:23.5,acd_mm:3.1,k1_d:42.5,k2_d:44,k1_axis_deg:15,k2_axis_deg:105,cct_um:550,lens_thickness_mm:4.3,wtw_mm:11.8,incision_axis_deg:180,sia_d:.25,prior_corneal_surgery:'NONE'});
const data={patientName:'Case Test',age:61,sex:'Female',loadedEyes:['OD','OS'],catalog:[{id:'clareon-panoptix-toric-cnwtt3',manufacturer:'Alcon',subtype:'Toric'},{id:'tecnis-puresee-den00v',manufacturer:'Johnson & Johnson',subtype:null}],plans:{OD:{selected_lens_id:'clareon-panoptix-toric-cnwtt3',route:'MANUFACTURER_TORIC',inputs:eye('OD'),target_refraction_d:-.25,a_constant:119.1},OS:{selected_lens_id:'tecnis-puresee-den00v',route:'COOKE_K6',inputs:eye('OS'),target_refraction_d:-.5,a_constant:119.3}}};
(async()=>{const transfer=ctx.window.CERAI_ESCRS_ASSISTANT.transfer;
 const newTab=()=>({closed:false,location:{replace:u=>{destination=u;}},close(){this.closed=true;}});
 const send=()=>transfer(data,undefined,newTab());
 assert.equal(await send(),true);assert(destination.includes('/live/'));assert.equal(navigations,0);
 const firstNavigation=navigations;fail=true;await assert.rejects(send(),/Verification failed/);assert.equal(navigations,firstNavigation);
 fail=false;validation="consent_version";await assert.rejects(send(),/Reload CER-AI/);
 validation="eyes";await assert.rejects(transfer(data),/Review the patient details/);
 consent=false;const before=posts;assert.equal(await send(),false);assert.equal(posts,before);assert.equal(navigations,firstNavigation);
 consent=true;validation=null;provider="browserbase";assert.equal(await transfer(data),true);assert(destination.includes("/iol/escrs-session/"));
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    result = subprocess.run(["node", "-e", script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr


def test_iol_page_changes_asset_url_when_transfer_script_changes(monkeypatch):
    import re
    from iol_module.ui import render_iol_html
    before = render_iol_html()
    read_bytes = Path.read_bytes
    def changed(path):
        content = read_bytes(path)
        return content + b"\n// next release" if path.name == "iol-escrs-assistant.js" else content
    monkeypatch.setattr(Path, "read_bytes", changed)
    after = render_iol_html()
    pattern = r'/static/iol-escrs-assistant.js\?v=[^" ]+'
    assert re.search(pattern, before)[0] != re.search(pattern, after)[0]
    assert '/static/iol-escrs-assistant.js?v=2"' not in before


def test_five_minute_viewer_has_preparation_budget_and_matching_keepalive(monkeypatch):
    from urllib.parse import parse_qs, urlsplit
    monkeypatch.setenv("BROWSERLESS_SESSION_SECONDS", "300")
    query = build_query(CloudTransfer.model_validate(case()))
    assert "liveURL(detached:true,timeout:300000" in query
    assert "reconnect(timeout:300000)" in query
    with patch("iol_module.escrs_cloud.urlopen", return_value=upstream()) as fetch:
        result = create_cloud_transfer(CloudTransfer.model_validate(case()), "doctor")
        assert parse_qs(urlsplit(fetch.call_args.args[0].full_url).query)["timeout"] == ["425000"]
        assert result["viewer_limit_seconds"] == 300
        assert result["session_limit_seconds"] == 425
        with pytest.raises(HTTPException) as caught:
            create_cloud_transfer(CloudTransfer.model_validate(case()), "doctor")
        assert caught.value.status_code == 429
        assert 300 <= int(caught.value.headers["Retry-After"]) <= 426


def test_invalid_duration_fails_before_contacting_provider(monkeypatch):
    monkeypatch.setenv("BROWSERLESS_SESSION_SECONDS", "999999")
    with patch("iol_module.escrs_cloud.urlopen") as fetch:
        with pytest.raises(HTTPException) as caught:
            create_cloud_transfer(CloudTransfer.model_validate(case()), "doctor")
        assert caught.value.status_code == 503
        fetch.assert_not_called()
