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
    payload["eyes"]["OD"]["lens_id"] = "clareon-panoptix-toric-cnwtt3"
    payload["eyes"]["OS"]["lens_id"] = "tecnis-puresee-den00v"
    return payload


@pytest.fixture(autouse=True)
def clean_leases(monkeypatch):
    _leases.clear()
    monkeypatch.setenv("BROWSERLESS_TOKEN", "test-secret-do-not-return")
    monkeypatch.setenv("BROWSERLESS_HOST", "production-sfo.browserless.io")
    yield
    _leases.clear()


def test_cloud_input_rejects_wrong_model_manufacturer_mode_and_consent():
    for change in (
        lambda p: p.update(terms_accepted=False),
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


def test_cloud_routes_require_login_and_use_server_doctor_identity():
    from iol_module.web import install
    import operational_security
    core = SimpleNamespace(app=FastAPI())
    install(core)
    with TestClient(core.app) as client:
        assert client.get("/iol/escrs-cloud-config").status_code == 401
        assert client.post("/iol/escrs-cloud-transfer", json=case()).status_code == 401
        with patch("user_access.require_current_principal", return_value=SimpleNamespace(user_id="doctor", display_name="Signed-in Surgeon")), patch("iol_module.escrs_cloud.create_cloud_transfer", return_value={"verified": True}) as transfer:
            response = client.post("/iol/escrs-cloud-transfer", json=case())
            assert response.status_code == 200
            assert transfer.call_args.args[0].surgeon == "Signed-in Surgeon"
    assert "/iol/escrs-cloud-transfer" in operational_security.PROTECTED_PATHS


def test_mobile_web_handoff_closes_failed_popups_and_requires_consent():
    if not shutil.which("node"):
        pytest.skip("Node unavailable")
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const names=JSON.parse(fs.readFileSync('static/escrs-models.json','utf8'));
let consent=true,fail=false,destination,closed=false,opens=0;
const ctx={URL,window:{confirm:()=>consent,open:()=>{opens++;return {opener:{},document:{body:{}},location:{replace:u=>destination=u},close:()=>closed=true};}},fetch:async(url,options)=>{
 if(url==='/auth/me')return {ok:true,json:async()=>({user:{display_name:'Signed-in Doctor'}})};
 if(url==='/iol/escrs-cloud-config')return {ok:true,json:async()=>({enabled:true,models:names})};
 assert.equal(url,'/iol/escrs-cloud-transfer');const p=JSON.parse(options.body);
 assert.equal(p.terms_accepted,true);assert.equal(p.surgeon,'Signed-in Doctor');
 assert.equal(p.eyes.OD.toric,true);assert.equal(p.eyes.OS.toric,false);
 assert.equal(p.initials,'CT');assert(!JSON.stringify(p).includes('Case Test'));
 return {ok:!fail,json:async()=>fail?{detail:'Verification failed'}:{escrs_url:'https://production-sfo.browserless.io/e/x/live/index.html?i=viewer'}};
}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/iol-escrs-assistant.js','utf8'),ctx);
const eye=side=>({eye:side,biological_sex:'Female',axial_length_mm:23.5,acd_mm:3.1,k1_d:42.5,k2_d:44,k1_axis_deg:15,k2_axis_deg:105,cct_um:550,lens_thickness_mm:4.3,wtw_mm:11.8,incision_axis_deg:180,sia_d:.25,prior_corneal_surgery:'NONE'});
const data={patientName:'Case Test',age:61,sex:'Female',loadedEyes:['OD','OS'],catalog:[{id:'clareon-panoptix-toric-cnwtt3',manufacturer:'Alcon',subtype:'Toric'},{id:'tecnis-puresee-den00v',manufacturer:'Johnson & Johnson',subtype:null}],plans:{OD:{selected_lens_id:'clareon-panoptix-toric-cnwtt3',route:'MANUFACTURER_TORIC',inputs:eye('OD'),target_refraction_d:-.25,a_constant:119.1},OS:{selected_lens_id:'tecnis-puresee-den00v',route:'COOKE_K6',inputs:eye('OS'),target_refraction_d:-.5,a_constant:119.3}}};
(async()=>{const transfer=ctx.window.CERAI_ESCRS_ASSISTANT.transfer;
 assert.equal(await transfer(data),true);assert(destination.includes('/live/'));
 fail=true;await assert.rejects(transfer(data),/Verification failed/);assert(closed);
 consent=false;const before=opens;assert.equal(await transfer(data),false);assert.equal(opens,before);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    result = subprocess.run(["node", "-e", script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
