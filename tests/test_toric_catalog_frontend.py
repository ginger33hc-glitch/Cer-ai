"""Model descriptors survive rendering; unsupported-series warning translates."""
import json
from pathlib import Path
import subprocess

from iol_module.toric_catalog import VERIFIED_LENS_STEPS


def test_all_toric_model_descriptors_render_and_warning_is_turkish():
    script = r'''
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const context={window:{}, localStorage:{getItem:()=> 'tr'},
  document:{readyState:'loading',documentElement:{},addEventListener:()=>{}}};
vm.runInNewContext(fs.readFileSync('static/i18n.js','utf8'),context);
const tr=context.window.CERAI_I18N.translate;
assert.equal(tr('No validated embedded model series for this lens. Use the manufacturer calculator and ESCRS for independent verification.'),
  'Bu lens için uygulama içinde doğrulanmış model serisi bulunmuyor. Bağımsız kontrol için üretici hesaplayıcısını ve ESCRS’yi kullanın.');
const source=fs.readFileSync('static/iol.js','utf8');
const start=source.indexOf('      if(toricRoute && data.toric_candidates?.length)');
const block=source.slice(start,source.indexOf('      if(data.predictions?.length)',start));
for(const model of JSON.parse(process.argv[1])) {
  const state={html:'',notes:'',toricRoute:true,lensCatalog:[],formula:'Cooke K6',tr,
    data:{toric_candidates:[{model,cylinder_iol_d:2.25,marker_axis_deg:90,
    spherical_equivalent_iol_d:21,residual_spectacle_cylinder_d:0.1,residual_spectacle_axis_deg:90}]}};
  vm.runInNewContext(block,state);
  assert(state.html.includes(`<td>${model}</td>`),model);
  assert(!state.html.includes('TEST ONLY'));
  assert(state.notes.includes('TEST ONLY'));
}
'''
    subprocess.run(["node", "-e", script, json.dumps([
        model for steps in VERIFIED_LENS_STEPS.values() for model in steps
    ])], cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True, text=True)
