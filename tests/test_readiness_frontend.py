"""Pure JavaScript unit checks; no browser, network, or patient data."""
from pathlib import Path
import shutil
import subprocess

import pytest

import assessment_workflow

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_js_syntax_and_manual_role_preservation():
    if not shutil.which('node'):
        pytest.skip('Node is not available')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8');
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))new vm.Script(match[1]);
new vm.Script(fs.readFileSync('static/assessment-readiness.js','utf8'));
const fields={};
for(const eye of ['od','os'])for(const suffix of ['manifest_sphere','manifest_cylinder','sphere','cylinder','axis'])fields['#'+eye+'_'+suffix]={value:''};
fields['#od_manifest_sphere'].value='−7,50';fields['#od_manifest_cylinder'].value='-1.50';fields['#od_axis'].value='8';
fields['#os_manifest_sphere'].value='-4';
const context={document:{querySelector:key=>fields[key]},value:key=>String(fields['#'+key].value),cardTransferNote:{},correctionText:()=>''};
vm.createContext(context);
vm.runInContext(html.slice(html.indexOf('function applyEffectivePlans('),html.indexOf('function listBlock(')),context);
context.applyEffectivePlans({OD:{correction_source:'card',manifest_sphere_D:-6,manifest_cylinder_magnitude_D:2,intended_sphere_D:-6,intended_cylinder_magnitude_D:2,correction_axis_deg:90},OS:{correction_source:'card',manifest_sphere_D:-6,manifest_cylinder_magnitude_D:2}});
assert.equal(fields['#od_manifest_sphere'].value,'−7,50');assert.equal(fields['#od_manifest_cylinder'].value,'-1.50');assert.equal(fields['#od_axis'].value,'8');
assert.equal(fields['#od_sphere'].value,-6);assert.equal(fields['#od_cylinder'].value,-2);
assert.equal(fields['#os_manifest_cylinder'].value,'');
fields['#os_manifest_sphere'].value='';
context.applyEffectivePlans({OS:{manifest_source:'TREATMENT_CARD_DUZELTME_MIKTARI',intended_source:'TREATMENT_CARD_DUZELTME_MIKTARI',manifest_entered_sphere_D:3,manifest_cylinder_signed_D:0,manifest_axis_deg:0,intended_entered_sphere_D:3,intended_cylinder_signed_D:0,intended_axis_deg:0}});
assert.equal(fields['#os_manifest_sphere'].value,3);assert.equal(fields['#os_manifest_cylinder'].value,0);
assert.equal(fields['#os_sphere'].value,3);assert.equal(fields['#os_cylinder'].value,0);assert.equal(fields['#os_axis'].value,0);
const ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/assessment-readiness.js','utf8'),ctx);
const panel={hidden:false,replaceChildren(){},querySelectorAll(){return this.inputs||[];}};
const readiness=new ctx.window.HCReadiness(panel);
panel.inputs=[{value:'−0,61',tagName:'INPUT',dataset:{eye:'OD',measurement:'I_S'}}];
assert.equal(readiness.collect().OD.I_S,-.61);
panel.inputs=[{value:'YES',tagName:'SELECT',dataset:{eye:'OS',measurement:'srax'}}];
assert.equal(readiness.collect().OS.srax,'YES');
panel.inputs=[];assert.deepEqual(readiness.collect(),{});assert.deepEqual(readiness.overrides,{});
panel.inputs=[{value:'NO',tagName:'SELECT',dataset:{eye:'OS',measurement:'srax'}}];
assert.equal(readiness.collect().OS.srax,'NO');
panel.inputs=[{value:'512',tagName:'INPUT',dataset:{eye:'OD',measurement:'pachy_thinnest_um'}}];
assert.equal(readiness.collect().OD.pachy_thinnest_um,512);
panel.inputs=[{value:'APPROVE_CONTINUE',dataset:{sourceConfirmation:'pentacam_exam_date_conflict'}}];
assert.equal(readiness.collectSourceConfirmations().pentacam_exam_date_conflict,'APPROVE_CONTINUE');
panel.inputs=[];assert.deepEqual(readiness.collectSourceConfirmations(),{});
panel.inputs=[{value:'APPROVE_CONTINUE',dataset:{sourceConfirmation:'pentacam_exam_date_conflict'}}];
panel.inputs[0].value='wrong';assert.throws(()=>readiness.collect());
readiness.reset();assert.equal(readiness.token,null);assert.equal(panel.hidden,true);
'''
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_hidden_reports_stay_hidden_when_printing_and_after_edits():
    html = (ROOT / 'static/index.html').read_text()
    assert '.report-card[hidden]{display:none!important}' in html
    assert "if(lastReport&&!reportCard.hidden)window.print()" in html
    assert "f.addEventListener('input',()=>{reportCard.hidden=true;lastReport=null;})" in html
    assert "f.addEventListener('change',()=>{reportCard.hidden=true;lastReport=null;})" in html


def test_completion_answers_sync_before_validation_and_payload_serialization():
    html = (ROOT / 'static/index.html').read_text()
    readiness = (ROOT / 'static/assessment-readiness.js').read_text()
    submit_start = html.index('f.addEventListener("submit"')
    submit_end = html.index('if("serviceWorker" in navigator)', submit_start)
    submit = html[submit_start:submit_end]

    collect = submit.index('clinicalOverrides=readiness.collect()')
    form_validation = submit.index('validateRefractionInputs()')
    modifiers = submit.index('modifiers=patientModifiers()')
    completion_request = submit.index("ceraiFetch('/assessment/complete'")
    assert collect < form_validation < modifiers < completion_request
    assert submit.count('readiness.collect()') == 1
    assert 'input.dataset.sourceForm=item.form_id;input.required=true' in readiness
    assert 'if(input){this.hasCompletableInputs=true;input.required=true;' in readiness


def test_ablation_field_rejects_negative_typing_and_paste_but_accepts_zero():
    if not shutil.which("node"):
        pytest.skip("Node is not available")
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8');
class Field{
  constructor(){this.value='';this.validity='';this.listeners={};this.reports=0;}
  addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
  setCustomValidity(message){this.validity=message;}
  reportValidity(){this.reports++;}
  dispatch(type,event={}){for(const fn of this.listeners[type]||[])fn(event);}
}
const fields={od_ablation:new Field(),os_ablation:new Field()};
const context={document:{getElementById:id=>fields[id]},Number,String};
vm.createContext(context);
const start=html.indexOf('function enforceNonnegativeAblation');
const end=html.indexOf('const f = document.querySelector',start);
vm.runInContext(html.slice(start,end),context);
let prevented=false;
fields.od_ablation.dispatch('keydown',{key:'-',preventDefault(){prevented=true;}});
assert.equal(prevented,true);assert.notEqual(fields.od_ablation.validity,'');
fields.od_ablation.value='-12.5';fields.od_ablation.dispatch('input');
assert.equal(fields.od_ablation.value,'');assert.notEqual(fields.od_ablation.validity,'');
fields.od_ablation.value='0';fields.od_ablation.dispatch('input');
assert.equal(fields.od_ablation.value,'0');assert.equal(fields.od_ablation.validity,'');
'''
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_preassessment_source_confirmation_and_refraction_prompt_are_visible():
    html = (ROOT / 'static/index.html').read_text()
    translations = (ROOT / 'static/i18n.js').read_text()
    assert 'id="sourceSetStatus"' in html
    assert 'summary.required_sources.map' in html
    assert 'summary.optional_treatment_card' in html
    assert 'MANDATORY_SOURCE_SET_INCOMPLETE' in html
    assert 'PREASSESSMENT_REFRACTION_REQUIRED' in html
    assert 'errorDetail.missing_refraction?.[0]' in html
    for label in (
        'Required image confirmation', 'Optional treatment card', 'present',
        'missing', 'not provided', 'unreadable — enter refraction',
        'No treatment card was provided.', 'The optional treatment card was unreadable.',
    ):
        assert label in translations


def test_manifest_defaults_intended_until_surgeon_edits_intended():
    if not shutil.which('node'):
        pytest.skip('Node is not available')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8');
class Field{
  constructor(){this.value='';this.listeners={};}
  addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
  dispatchEvent(event){for(const fn of this.listeners[event.type]||[])fn(event);}
}
const fields={};
for(const eye of ['od','os'])for(const suffix of ['manifest_sphere','manifest_cylinder','sphere','cylinder','axis'])fields[`${eye}_${suffix}`]=new Field();
const context={document:{getElementById:id=>fields[id]},Event:class{constructor(type){this.type=type;}},numberOrNull:id=>{const raw=fields[id].value.trim();return raw===''?null:Number(raw);}};
vm.createContext(context);
const start=html.indexOf('// Manifest is the surgeon');
const end=html.indexOf('const clinicalReviewState',start);
vm.runInContext(html.slice(start,end),context);
fields.od_manifest_sphere.value='-3.25';fields.od_manifest_sphere.dispatchEvent(new context.Event('input'));
assert.equal(fields.od_sphere.value,'-3.25');
fields.od_manifest_cylinder.value='-1.50';fields.od_manifest_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.od_cylinder.value,'-1.50');
fields.od_sphere.value='-2.75';fields.od_sphere.dispatchEvent(new context.Event('input'));
fields.od_manifest_sphere.value='-4.00';fields.od_manifest_sphere.dispatchEvent(new context.Event('input'));
assert.equal(fields.od_sphere.value,'-2.75');
fields.od_manifest_cylinder.value='-2.00';fields.od_manifest_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.od_cylinder.value,'-2.00');
fields.os_manifest_sphere.value='-2.00';fields.os_manifest_sphere.dispatchEvent(new context.Event('input'));
fields.os_manifest_cylinder.value='0';fields.os_manifest_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.os_manifest_cylinder.value,'0');
assert.equal(fields.os_cylinder.value,'0');
assert.equal(fields.os_axis.value,'0');
fields.os_manifest_sphere.value='0';fields.os_manifest_sphere.dispatchEvent(new context.Event('input'));
assert.equal(fields.os_sphere.value,'-2.00');
// Numeric zero remains linked, including intermediate zero-like text.
fields.os_manifest_cylinder.value='0.';fields.os_manifest_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.os_manifest_cylinder.value,'0.');
assert.equal(fields.os_cylinder.value,'0.');
assert.equal(fields.os_axis.value,'0');
fields.os_manifest_cylinder.value='';fields.os_manifest_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.os_manifest_cylinder.value,'');
assert.equal(fields.os_cylinder.value,'');
assert.equal(fields.os_axis.value,'');
fields.os_manifest_cylinder.value='-1.25';fields.os_manifest_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.os_manifest_cylinder.value,'-1.25');
assert.equal(fields.os_cylinder.value,'-1.25');
assert.equal(fields.os_axis.value,'');
// An axis synthesized for spherical treatment cannot survive a surgeon change
// to nonzero intended cylinder.
fields.os_manifest_cylinder.value='0';fields.os_manifest_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.os_cylinder.value,'0');
assert.equal(fields.os_axis.value,'0');
fields.os_cylinder.value='-0.50';fields.os_cylinder.dispatchEvent(new context.Event('input'));
assert.equal(fields.os_cylinder.value,'-0.50');
assert.equal(fields.os_axis.value,'');
'''
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_patient_age_completion_uses_one_shared_field():
    item = assessment_workflow._request('PATIENT', 'age', {})
    readiness = (ROOT / 'static/assessment-readiness.js').read_text()
    html = (ROOT / 'static/index.html').read_text()
    translations = (ROOT / 'static/i18n.js').read_text()
    assert '<label>Patient age (years)</label>' in html
    assert '/static/assessment-readiness.js?v=9' in html
    assert 'Pentacam age unreadable; enter years' not in html
    assert 'Pentacam yaşı okunamadı; yıl olarak girin' not in translations
    assert item == {
        'eye': 'PATIENT',
        'label': 'Patient age (years)',
        'kind': 'form',
        'key': 'age',
        'destination': 'source',
        'form_id': 'age',
        'help': "Enter the patient's age in whole years.",
        'required_for': ['Randleman'],
        'source_screen': 'Pentacam patient identity / surgeon entry',
        'source_box': 'Patient age',
    }
    assert 'item.form_id===\'age\'' in readiness
    assert 'originalRow.hidden=true' in readiness
    assert 'original.required=false;input.required=true' in readiness
    assert 'input.dataset.sourceForm=item.form_id' in readiness
    assert "this.panel.querySelectorAll('[data-source-form]')" in readiness
    assert 'original.value=input.value' in readiness
    assert 'seek_patient_age=age is None' in (ROOT / 'app.py').read_text()


def test_image_change_preserves_surgeon_age_but_discards_old_derived_age():
    if not shutil.which('node'):
        pytest.skip('Node is not available')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8');
const start=html.indexOf('function resetAgeAcquisition()');
const end=html.indexOf('function renderSelectedFiles',start);
const context={
  ageInput:{value:'61',readOnly:false,required:true},
  manualAgeRow:{hidden:false}
};
vm.createContext(context);vm.runInContext(html.slice(start,end),context);
context.resetAgeAcquisition();
assert.equal(context.ageInput.value,'61');
assert.equal(context.ageInput.readOnly,false);
assert.equal(context.manualAgeRow.hidden,false);
context.ageInput.value='44';context.ageInput.readOnly=true;context.ageInput.required=false;
context.resetAgeAcquisition();
assert.equal(context.ageInput.value,'');
assert.equal(context.ageInput.readOnly,false);
assert.equal(context.manualAgeRow.hidden,true);
'''
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_nice_measurements_are_requested_only_after_canonical_reading_fails():
    html = (ROOT / 'static/index.html').read_text()
    assert 'nice_confirmation' not in html
    assert 'nice_central' not in html
    assert 'nice_pe' not in html
    assert 'surgeon_nice_' not in html

    central = assessment_workflow._request('OD', 'NICE: central_pachy_um', {})
    posterior = assessment_workflow._request('OD', 'NICE: B_Ele_Th_um', {})
    assert central['kind'] == posterior['kind'] == 'number'
    assert central['key'] == 'central_pachy_um'
    assert posterior['key'] == 'B_Ele_Th_um'
    assert 'Pupil Center (+)' in central['label']
    assert 'B. Ele.Th' in posterior['label']


def test_only_unread_fields_can_request_a_temporary_source_region():
    workflow = (ROOT / 'assessment_workflow.py').read_text()
    readiness = (ROOT / 'static/assessment-readiness.js').read_text()
    html = (ROOT / 'static/index.html').read_text()
    assert '"source_region": True' in workflow
    assert '/assessment/source-region' in workflow
    assert "if(item.source_region)" in readiness
    assert "assessment_token:this.token" in readiness
    assert "source_region_count" in readiness
    assert "index})" in readiness
    assert 'Pentacam/topography region the application could not read' in readiness
    assert '.completion-with-source>input,.completion-with-source>select{grid-column:2' in html
    assert '.completion-source-region{grid-column:1' in html


def test_supplemental_ablation_serialization_and_edit_invalidation():
    if not shutil.which('node'):
        pytest.skip('Node is not available')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('static/index.html','utf8');
const fields={};
for(const prefix of ['od','os'])for(const suffix of ['lasik_a_ablation_um','lasik_bc_ablation_um','ablation','procedure'])fields[`${prefix}_${suffix}`]={value:''};
fields.os_procedure.value='LASIK';fields.os_ablation.value='40';
const copies=[{value:'35',dataset:{sourceForm:'os_lasik_bc_ablation_um'}}];
const ctx={window:{},document:{getElementById:id=>fields[id],querySelectorAll:selector=>selector.includes('os_lasik_bc_ablation_um')?copies:[]},
 value:id=>fields[id]?.value||'',numberOrNull:id=>fields[id]?.value?Number(fields[id].value):null};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/assessment-readiness.js','utf8'),ctx);
fields.os_lasik_bc_ablation_um.setCustomValidity=()=>{};
const panel={replaceChildren(){},querySelectorAll:selector=>selector==='[data-source-form]'?copies:[]};
const readiness=new ctx.window.HCReadiness(panel);readiness.collect();
vm.runInContext(html.slice(html.indexOf('function plan(prefix)'),html.indexOf('function statusClass')),ctx);
assert.equal(ctx.plan('os').ablation_um,40);assert.equal(ctx.plan('os').lasik_bc_ablation_um,35);
vm.runInContext(html.slice(html.indexOf('function invalidateSupplementaryAblations'),html.indexOf("f.addEventListener('input',invalidateSupplementaryAblations)")),ctx);
ctx.invalidateSupplementaryAblations({target:{id:'os_sphere'}});
assert.equal(ctx.plan('os').lasik_bc_ablation_um,null);assert.equal(copies[0].value,'');
assert.equal(ctx.plan('os').ablation_um,40);
'''
    subprocess.run(['node','-e',script],cwd=ROOT,check=True,capture_output=True,text=True)


@pytest.mark.parametrize("width", [390, 1280])
def test_zone_completion_browser_transfers_visible_answer(width):
    import os
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        executable = (os.environ.get("CERAI_CHROMIUM_EXECUTABLE") or shutil.which("google-chrome")
                      or shutil.which("chromium") or playwright.chromium.executable_path)
        if not Path(executable).is_file():
            pytest.skip("Chromium unavailable")
        browser = playwright.chromium.launch(executable_path=executable, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.set_content('<form><input id="os_ablation" value="40"><div hidden><input type="number" id="os_lasik_bc_ablation_um" min="0" step=".1"></div><div id="panel"></div></form>')
        page.add_script_tag(content=(ROOT / "static/assessment-readiness.js").read_text())
        page.evaluate("""() => {
          window.readiness=new HCReadiness(document.getElementById('panel'));
          readiness.show({assessment_token:'synthetic',workflow_status:'NEEDS_INPUT',input_requests:[{
            eye:'OS',key:'lasik_bc_ablation_um',form_id:'os_lasik_bc_ablation_um',kind:'form',destination:'source',
            label:'Plan B/C — OZ 6.0 / TZ 8.5',help:'Original depth retained.'}]});
        }""")
        page.locator('#completion_1').fill('35')
        page.evaluate('readiness.collect()')
        assert page.locator('#os_lasik_bc_ablation_um').input_value() == '35'
        assert page.locator('#os_ablation').input_value() == '40'
        assert page.locator('form').evaluate('(form)=>form.checkValidity()')
        browser.close()
