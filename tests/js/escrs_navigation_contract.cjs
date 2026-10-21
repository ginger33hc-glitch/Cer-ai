const fs=require('fs'),vm=require('vm'),assert=require('assert');
let resolveTransfer, mode='ok', destinations=[];
const data={patientName:'Synthetic Test',age:61,sex:'Female',loadedEyes:['OD'],catalog:[{id:'lens',manufacturer:'Alcon'}],plans:{OD:{selected_lens_id:'lens',route:'COOKE_K6',inputs:{eye:'OD',biological_sex:'Female'},target_refraction_d:0,a_constant:119}}};
const ctx={URL,window:{location:{origin:'https://cer-ai.com',assign:u=>destinations.push(u)},confirm:()=>true},fetch:async(url)=>{
 if(url==='/auth/me')return {ok:true,json:async()=>({user:{display_name:'Synthetic Surgeon'}})};
 if(url==='/iol/escrs-cloud-config')return {ok:true,json:async()=>({enabled:true,provider:'browserbase',models:{lens:'Lens'}})};
 return new Promise(r=>{resolveTransfer=()=>r({ok:mode!=='error',status:mode==='error'?503:200,json:async()=>mode==='error'?{detail:'Unavailable'}:{escrs_url:mode==='bad'?'https://evil.example/':'https://cer-ai.com/iol/escrs-session/'+'a'.repeat(32)}});});
}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/iol-escrs-assistant.js','utf8'),ctx);
(async()=>{
 const transfer=ctx.window.CERAI_ESCRS_ASSISTANT.transfer;
 for(const scenario of ['ok','error','bad']){
  mode=scenario;resolveTransfer=null;destinations=[];
  const pending=transfer(data,()=>{},null,true);
  for(let i=0;i<10&&!resolveTransfer;i++)await Promise.resolve();
  assert(resolveTransfer);assert.equal(destinations.length,0,'Must remain on calculation while preparing');
  resolveTransfer();
  if(scenario==='ok'){assert.equal(await pending,true);assert.equal(destinations.length,1);assert(destinations[0].startsWith('https://cer-ai.com/iol/escrs-session/'));}
  else{await assert.rejects(pending);assert.equal(destinations.length,0,'Failure or invalid URL must retain calculation');}
 }
 console.log('ESCRS delayed same-tab navigation and failure tests passed');
})().catch(e=>{console.error(e);process.exitCode=1});
