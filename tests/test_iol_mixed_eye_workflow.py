"""Mixed toric/non-toric cases must not silently block a ready eye."""
from pathlib import Path
import subprocess


def test_partial_selection_and_stage_specific_completion():
    script = r'''
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const source=fs.readFileSync('static/iol.js','utf8');
const start=source.indexOf('  async function runLoadedEyes(method)');
const fn=source.slice(start,source.indexOf('  $("recommendAll").addEventListener',start));
(async()=>{
  const status={textContent:''}, calls=[];
  let selected={OD:false,OS:true};
  const controllers=new Map(['OD','OS'].map(eye=>[eye,{
    readyToCalculate:()=>selected[eye],readyToRecommend:()=>true,evaluated:()=>true,
    recommend:async()=>true,calculate:async()=>{calls.push(eye);return selected[eye];}
  }]));
  const context={caseVersion:1,workflowBusy:false,loadedEyes:['OD','OS'],controllers,
    $:id=>id==='patientForm'?{reportValidity:()=>true}:status,syncWorkflow:()=>{},tr:x=>x};
  vm.createContext(context);vm.runInContext(fn,context);
  const syncStart=source.indexOf('  function syncWorkflow()');
  const sync=source.slice(syncStart,source.indexOf('  let lensCatalog',syncStart));
  const ui=new Map();
  for(const id of ['reviewStage','recommendAll','calculationActions','calculateAll','extractButton','sourceImages']) ui.set(id,{});
  controllers.forEach(c=>{c.recommendationShown=()=>true;});
  const syncContext={...context,$:id=>ui.get(id),window:{},powerPlans:{OD:null,OS:null}};
  vm.createContext(syncContext);vm.runInContext(sync+';syncWorkflow();',syncContext);
  assert.equal(ui.get('calculateAll').disabled,false);
  const calcStart=source.indexOf('  async function calculate()');
  const calcEnd=source.indexOf('    const corneaBack =',calcStart);
  const calcPrefix=source.slice(calcStart,calcEnd)+'return true; }';
  const lens={value:'',reportValidity:()=>false}, powerStatus={};
  const calcContext={version:0,eye:'OD',powerPlans:{OD:{}},syncWorkflow:()=>{},showCalculationNotes:()=>{},calculationRoot:{hidden:true},
    $:id=>id==='selectedLens'?lens:id==='powerStatus'?powerStatus:{replaceChildren:()=>{}},tr:x=>x};
  vm.createContext(calcContext);vm.runInContext(calcPrefix,calcContext);
  assert.equal(await calcContext.calculate(),false);
  assert.equal(powerStatus.textContent,'OD: Select a clinic lens.');
  assert.equal(calcContext.calculationRoot.hidden,false);
  await context.runLoadedEyes('recommend');
  assert.equal(status.textContent,'Recommendation generated. Select the lens for Stage 2.');
  await context.runLoadedEyes('calculate');
  assert.deepEqual(calls,['OD','OS']);
  assert.equal(status.textContent,"Review each eye's status and complete any missing fields.");
  selected.OD=true;calls.length=0;
  await context.runLoadedEyes('calculate');
  assert.deepEqual(calls,['OD','OS']);
  assert.equal(status.textContent,'Completed. Review the separate OD and OS results below.');
  assert.equal(context.workflowBusy,false);
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                   check=True, capture_output=True, text=True)
