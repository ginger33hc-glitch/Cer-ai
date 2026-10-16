// A DOM contract fixture, not a browser or an ESCRS end-to-end test.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Input {
  constructor(name,type='number',value='') {this.labels=[{textContent:name}];this.type=type;this.value=value;this.checked=false;this.disabled=false;this.readOnly=false;this.events=[];}
  get value(){return this._value;}
  set value(v){this._value=String(v);}
  getAttribute(){return null;}
  focus(){} blur(){} dispatchEvent(e){this.events.push(e.type);}
  click(){if(this.type==='checkbox')this.checked=!this.checked;else if(this.options)openOptions(this);}
}
class Combo {
  constructor(name,value,options){this.name=name;this.textContent=value;this.options=options;}
  getAttribute(key){return key==='aria-label'?this.name:key==='role'?'combobox':null;}
  click(){throw Error("MudSelect requires mousedown");}
  dispatchEvent(e){if(e.type==='mousedown')openOptions(this);}
}
let options=[];
function openOptions(control){options=control.options.map(text=>({textContent:text,getClientRects:()=>[1],click(){if(control instanceof Combo)control.textContent=text;else control.value=text;options=[];}}));}
function makeRoot(side) {
  const fields={};
  for(const n of ['AL','ACD','LT','CCT','WTW','K1','K2','Target Refraction','Cooke A-Constant','K1 axis','K2 axis','Incision','SIA'])fields[n]=new Input(n);
  for(const n of ['Toric','Keratoconus','Argos (SoS) AL','Post LASIK/PRK/RK'])fields[n]=new Input(n,'checkbox');
  fields.Index=new Combo('Index','1.3375',['1.3375']);
  fields.Manufacturer=new Combo('Manufacturer','',['Alcon','Johnson and Johnson Vision']);
  fields['Select IOL']=new Input('Select IOL','text');fields['Select IOL'].options=['Clareon PanOptix Toric CNWTT2-6','DEN00V'];
  const heading={textContent:side==='OD'?'OD Right':'OS Left',closest:()=>root};
  const root={fields,heading,querySelectorAll:s=>s==='h5'?[heading]:Object.values(fields)};return root;
}
function fixture() {
  const OD=makeRoot('OD'),OS=makeRoot('OS'),fields={};
  for(const n of ['Surgeon','Patient Initials','Id'])fields[n]=new Input(n,'text');
  fields.Age=new Input('Age');fields.Gender=new Combo('Gender','Male',['Male','Female']);
  // Hidden MudBlazor inputs have no labels; visible div[role=combobox] carries the value.
  const hidden=new Input('','hidden');
  const document={querySelectorAll:s=>s==='h5'?[OD.heading,OS.heading]:s==='[role="option"]'?options:s==='[role="dialog"]'?[]:[...Object.values(fields),hidden,...Object.values(OD.fields),...Object.values(OS.fields)]};
  const ctx={document,HTMLInputElement:Input,Event:class{constructor(type){this.type=type;}},KeyboardEvent:class{},MouseEvent:class{constructor(type){this.type=type;}},setTimeout:fn=>{fn();},Date};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync('extensions/escrs-assistant/adapter.js','utf8'),ctx);
  return {OD,OS,fields,run:ctx.CeraiEscrsAdapter.run};
}
const base={toric:true,axial_length_mm:23.5,acd_mm:3.1,k1_d:42.5,k2_d:44,k1_axis_deg:15,k2_axis_deg:105,cct_um:550,lens_thickness_mm:null,wtw_mm:11.8,incision_axis_deg:180,sia_d:.25,target_refraction_d:-.25,a_constant:119.1,prior_corneal_surgery:'NONE',manufacturer_matches:['Alcon'],lens_matches:['Clareon PanOptix Toric CNWTT2-6']};
const payload=()=>({version:1,surgeon:'Synthetic Surgeon',initials:'TT',age:61,sex:'Female',eyes:{OD:{...base},OS:{...base,toric:false,axial_length_mm:24.2,target_refraction_d:-.5,a_constant:119.3,manufacturer_matches:['Johnson and Johnson Vision'],lens_matches:['DEN00V']}}});
(async()=>{
 let f=fixture();f.OD.fields.LT.value='5';const result=await f.run(payload());
 assert.equal(result.OD,base.lens_matches[0]);assert.equal(result.OS,'DEN00V');
 assert.equal(f.fields.Gender.textContent,'Female');assert.equal(f.fields.Surgeon.value,'Synthetic Surgeon');assert.equal(f.fields.Age.value,'61');
 assert.equal(f.OD.fields.LT.value,'');assert.equal(f.OD.fields.AL.value,'23.5');assert.equal(f.OS.fields.AL.value,'24.2');
 assert.equal(f.OD.fields.Toric.checked,true);assert.equal(f.OS.fields.Toric.checked,false);
 assert.equal(f.OD.fields.Incision.value,'180');assert.equal(f.OD.fields.SIA.value,'0.25');
 assert.equal(f.OS.fields['Cooke A-Constant'].value,'119.3');assert(f.OD.fields.AL.events.includes('change'));
 f=fixture();f.OD.fields['Select IOL'].options=['A different lens'];await assert.rejects(f.run(payload()),/No exact/);
 f=fixture();f.OS.fields.AL.value='22';let p=payload();delete p.eyes.OS;await assert.rejects(f.run(p),/unused eye/);
 f=fixture();f.OD.fields.Keratoconus.checked=true;await assert.rejects(f.run(payload()),/keratoconus/);
 f=fixture();f.OD.fields.AL.disabled=true;await assert.rejects(f.run(payload()),/not editable/);
 // A later eye's render overwriting an earlier eye must not produce success.
 f=fixture();const original=f.OS.fields.SIA.dispatchEvent.bind(f.OS.fields.SIA);
 f.OS.fields.SIA.dispatchEvent=e=>{original(e);f.OD.fields.AL.value='29';};p=payload();p.eyes.OS.toric=true;
 await assert.rejects(f.run(p),/AL read-back failed/);
 console.log('DOM contract scenarios passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
