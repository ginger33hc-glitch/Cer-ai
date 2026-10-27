from pathlib import Path
import subprocess


def test_upload_and_poll_recover_lost_responses_without_duplicate_work():
    script = r'''
const assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');
const vm = require('node:vm');
const fs = require('node:fs');
let offsets=[0,0,0], writes=0, starts=0, polls=0, lost=false;
const progress=[];
const context={window:{},document:{documentElement:{lang:'tr'}},crypto:webcrypto,Uint8Array,AbortController,
  setTimeout:(fn,ms)=>setTimeout(fn,ms===30000?30000:0),clearTimeout,
  fetch:async(url,opts={})=>{
    let data;
    if(url==='/iol/jobs') data={job_id:'one',status:'UPLOADING',offsets:offsets.slice()};
    else if(url.includes('/images/')) {
      const index=Number(url.match(/images\/(\d)/)[1]);
      const offset=Number(url.split('offset=')[1]);
      if(offset===offsets[index]) { offsets[index]+=opts.body.size; writes++; }
      if(!lost) {lost=true; throw new TypeError('Failed to fetch');}
      data={offset:offsets[index]};
    } else if(url.endsWith('/start')) { starts++; data={status:'READING',completed:0,total:3}; }
    else {polls++; if(polls===1)throw new TypeError('Failed to fetch'); data={status:'COMPLETED',result:{identity:'verified'}};}
    return {ok:true,json:async()=>data};
  }
};
vm.runInNewContext(fs.readFileSync('static/iol-jobs.js','utf8'),context);
(async()=>{
 const files=Array.from({length:3},(_,i)=>Object.assign(new Blob(['original']),{name:`${i}.jpg`}));
 const result=await context.window.CERAI_IOL_JOBS.extract({files,patientName:'QA',requestId:'same-id',onProgress:text=>progress.push(text)});
 assert.equal(result.identity,'verified'); assert.equal(writes,3); assert.equal(starts,1); assert.equal(polls,2);
 assert(progress.some(text=>text.includes('Yeniden bağlanılıyor')));
 // A clinical rejection terminates polling and lets the next attempt use a new ID.
 context.fetch=async()=>({ok:true,json:async()=>({job_id:'one',status:'FAILED',detail:'Eye mismatch'})});
 await assert.rejects(context.window.CERAI_IOL_JOBS.extract({files,patientName:'QA',requestId:'same-id'}),e=>e.message==='Eye mismatch'&&e.restartRequired);
})().catch(error=>{console.error(error);process.exitCode=1});
'''
    result = subprocess.run(['node','-e',script],cwd=Path(__file__).parents[1],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
