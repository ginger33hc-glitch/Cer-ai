const assert=require('node:assert/strict');
const InputQueue=require('../static/iol-escrs-local.js');
(async()=>{
  let release, sent=[], active=0, maximum=0, frames=0;
  const first=new Promise(resolve=>{release=resolve;});
  const queue=new InputQueue(async command=>{
    active++;maximum=Math.max(maximum,active);sent.push({...command});
    if(sent.length===1)await first;
    active--;
  },()=>{frames++;});
  const done=queue.send({kind:'scroll',delta:10});
  await Promise.resolve();
  // Simulate a mobile swipe while the first network round trip is outstanding.
  for(let i=0;i<100;i++)queue.send({kind:'scroll',delta:10});
  assert.equal(sent.length,1);
  release();await done;
  assert.equal(sent.length,2);assert.equal(sent.reduce((n,c)=>n+c.delta,0),1010);
  assert.equal(maximum,1);assert.equal(frames,2);assert.equal(queue.busy,false);
  sent=[];
  queue.send({kind:'edit',field:'1',text:'1'});
  queue.send({kind:'edit',field:'1',text:'12'});
  queue.send({kind:'edit',field:'1',text:'123'});
  queue.send({kind:'key',key:'Tab'});
  queue.send({kind:'edit',field:'2',text:'4'});
  await queue.send({kind:'edit',field:'2',text:''});
  assert.deepEqual(sent,[{kind:'edit',field:'1',text:'123'},{kind:'key',key:'Tab'},{kind:'edit',field:'2',text:''}]);
  sent=[];
  for(let i=0;i<8;i++)queue.send({kind:'scroll',delta:500});
  queue.send({kind:'click',x:2,y:3});
  await queue.drain();
  assert.equal(sent.slice(0,-1).reduce((n,c)=>n+c.delta,0),4000);
  assert(sent.slice(0,-1).every(c=>Math.abs(c.delta)<=1600));
  assert.equal(sent.at(-1).kind,'click');
  // An unconfirmed write must not be retried or allow queued commands to leak.
  let calls=0;
  const failing=new InputQueue(async()=>{calls++;throw Error('lost response');},()=>{});
  const rejected=failing.send({kind:'edit',field:'1',text:'42'});
  failing.send({kind:'click',x:1,y:1});
  await assert.rejects(rejected,/lost response/);
  assert.equal(calls,1);assert.equal(failing.busy,false);
  console.log('PASS: burst coalescing, final values, barriers, scroll bounds, single flight, failure cancellation');
})().catch(error=>{console.error(error);process.exitCode=1;});

(async()=>{
  const vm=require('node:vm'),fs=require('node:fs');
  const timers=[],events={},elements={};let frames=0,releaseInput;
  for(const id of ['screen','status','viewport','fields','pdf','close','timer'])elements[id]={
    dataset:{},addEventListener:(event,fn)=>{events[event]=fn;},
    replaceChildren(){},appendChild(){},getBoundingClientRect:()=>({left:0,top:0,width:420,height:820})
  };
  const context={Date,Promise,console,
    document:{body:{dataset:{session:'synthetic'}},getElementById:id=>elements[id]},
    window:{addEventListener(){}},URL:{createObjectURL:()=>'/frame',revokeObjectURL(){}},
    setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){},setInterval(){},clearInterval(){},
    fetch:async(url)=>{
      if(url.endsWith('/input'))await new Promise(resolve=>{releaseInput=resolve;});
      if(url.endsWith('/frame'))frames++;
      return {ok:true,json:async()=>url.endsWith('/status')?{seconds_remaining:900}:[],blob:async()=>({})};
    }
  };
  vm.runInNewContext(fs.readFileSync('static/iol-escrs-local.js','utf8'),context);
  const tick=()=>new Promise(resolve=>setImmediate(resolve));
  await tick();assert.equal(frames,1);
  events.wheel({preventDefault(){},deltaY:120});await tick();
  assert.equal(typeof releaseInput,'function');
  await timers.shift()();await tick();
  assert.equal(frames,2,'screen refresh must not wait behind slow input');
  releaseInput();await tick();
  console.log('PASS: frame refresh continues while an input request is delayed');
})().catch(error=>{console.error(error);process.exitCode=1;});
