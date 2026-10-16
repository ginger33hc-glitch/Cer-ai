"""Cross-eye and fail-closed contract tests for the optional browser assistant."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_bilateral_transfer_identity_and_rejection_contracts():
    if not shutil.which('node'):
        pytest.skip('Node is not available')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={window:{}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync('static/iol-escrs-assistant.js','utf8'),ctx);
vm.runInContext(fs.readFileSync('extensions/escrs-assistant/adapter.js','utf8'),ctx);
const build=ctx.window.CERAI_ESCRS_ASSISTANT.buildPayload, validate=ctx.CeraiEscrsAdapter.validate;
const catalog=[{id:'clareon-panoptix-toric-cnwtt3',manufacturer:'Alcon',subtype:'Toric'},
{id:'tecnis-puresee-den00v',manufacturer:'Johnson & Johnson',subtype:null}];
const eye=(side,al)=>({eye:side,biological_sex:'Female',axial_length_mm:al,acd_mm:3.1,
 k1_d:42.5,k2_d:44,k1_axis_deg:15,k2_axis_deg:105,incision_axis_deg:180,sia_d:.25,
 prior_corneal_surgery:'NONE',lens_thickness_mm:null,cct_um:550,wtw_mm:11.8});
const data={catalog,loadedEyes:['OD','OS'],patientName:'İpek Şen',age:61,sex:'Female',surgeon:'Test Surgeon',plans:{
 OD:{selected_lens_id:catalog[0].id,route:'MANUFACTURER_TORIC',inputs:eye('OD',23.5),target_refraction_d:-.25,a_constant:119.1},
 OS:{selected_lens_id:catalog[1].id,route:'COOKE_K6',inputs:eye('OS',24.2),target_refraction_d:-.5,a_constant:119.3}}};
const p=build(data);validate(p);
assert.equal(p.initials,'İŞ');assert.equal(p.surgeon,'Test Surgeon');assert.equal(p.age,61);
assert.equal(p.eyes.OD.lens_matches[0],'Clareon PanOptix Toric CNWTT2-6');
assert.equal(p.eyes.OS.lens_matches[0],'DEN00V');assert.equal(p.eyes.OS.manufacturer_matches[0],'Johnson and Johnson Vision');
assert.equal(p.eyes.OD.toric,true);assert.equal(p.eyes.OS.toric,false);
assert.equal(p.eyes.OD.axial_length_mm,23.5);assert.equal(p.eyes.OS.axial_length_mm,24.2);
assert.equal(p.eyes.OS.target_refraction_d,-.5);assert.equal(p.eyes.OD.incision_axis_deg,180);
assert.equal(p.eyes.OD.lens_thickness_mm,null);assert(!JSON.stringify(p).includes('İpek'));
const copy=()=>JSON.parse(JSON.stringify(data));
let d=copy();delete d.plans.OS;assert.throws(()=>build(d),/both eyes/);
d=copy();d.plans.OS.inputs.eye='OD';assert.throws(()=>build(d),/differ/);
d=copy();d.sex='Male';assert.throws(()=>build(d),/differ/);
d=copy();d.catalog[1].id=d.plans.OS.selected_lens_id='unknown';assert.throws(()=>build(d),/no verified/);
d=copy();d.plans.OS.route='MANUFACTURER_TORIC';assert.throws(()=>build(d),/toric lens family/);
d=copy();d.age=NaN;assert.throws(()=>build(d),/age/);
d=copy();d.loadedEyes=['OD'];assert.equal(Object.keys(build(d).eyes).length,1);
for (const [key,value] of [['k1_axis_deg',null],['sia_d',-1],['lens_thickness_mm',NaN],['cct_um',550.5],['prior_corneal_surgery','RK']]) {
 const bad=JSON.parse(JSON.stringify(p));bad.eyes.OD[key]=value;assert.throws(()=>validate(bad));
}
'''
    result = subprocess.run(['node', '-e', script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
