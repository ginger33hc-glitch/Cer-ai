"""Exercise fragmented progress streams and error/incomplete responses without a browser."""

import shutil
import subprocess

import pytest


def test_streaming_progress_parser():
    if not shutil.which("node"):
        pytest.skip("Node unavailable")
    script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/keratoconus.js','utf8');
const start=source.indexOf('const stages='),end=source.indexOf('function language()',start);
const elements=Object.fromEntries(['progressPanel','progressPercent','progressBar','busy'].map(id=>[id,{}]));
const context={progressState:null,$:id=>elements[id],tr:en=>en,locale:'tr',TextDecoder,Uint8Array};
vm.createContext(context);vm.runInContext(source.slice(start,end),context);
function response(events){
 const bytes=new TextEncoder().encode(events.map(e=>JSON.stringify(e)).join('\n')+'\n');
 const chunks=[];for(let i=0;i<bytes.length;i+=3)chunks.push(bytes.slice(i,i+3));
 return {ok:true,body:{getReader:()=>({read:async()=>chunks.length?{value:chunks.shift(),done:false}:{done:true},cancel:async()=>{},releaseLock:()=>{}})}};
}
(async()=>{
 const result=await context.readScreening(response([{type:'progress',code:'ANALYZING_IMAGES',percent:30,completed_images:2,total_images:5},{type:'progress',code:'ARCHIVING',percent:95},{type:'result',percent:100,result:{patient:{name:'İpek'}}}]));
 assert.equal(result.patient.name,'İpek');assert.equal(elements.progressBar.value,100);assert.equal(elements.progressPercent.textContent,'100%');
 context.progressState=null;
 await assert.rejects(()=>context.readScreening(response([{type:'progress',code:'VERIFYING_REQUIRED_VALUES',percent:70},{type:'error',detail:'Read failed'}])),/Read failed/);
 assert.equal(elements.progressBar.value,70);
 context.progressState=null;
 await assert.rejects(()=>context.readScreening(response([{type:'progress',code:'ANALYZING_IMAGES',percent:30}])),/connection ended/);
 assert.equal(elements.progressBar.value,30);
 context.showProgress({code:'UPLOAD_COMPLETE',percent:10});assert.equal(elements.progressBar.value,30);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
