const fs=require('fs'),vm=require('vm'),assert=require('assert');
let listener,tabId=0,records={},opened=[];
const chrome={runtime:{getURL:p=>'chrome-extension://test-id/'+p,onMessage:{addListener:f=>{listener=f;}}},
 storage:{session:{get:async k=>k===null?{...records}:Object.fromEntries([k].filter(x=>records[x]).map(x=>[x,records[x]])),set:async v=>{Object.assign(records,v);},remove:async keys=>{for(const k of Array.isArray(keys)?keys:[keys])delete records[k];}}},
 tabs:{create:async()=>({id:++tabId}),update:async(id,o)=>{opened.push({id,...o});},onRemoved:{addListener:()=>{}}}};
vm.runInNewContext(fs.readFileSync('extensions/escrs-assistant/background.js','utf8'),{chrome,URL,Date});
const send=(message,sender)=>new Promise(r=>listener(message,sender,r));
(async()=>{
 assert.equal((await send({action:'SELF_TEST'},{url:'https://cer-ai.com/iol',tab:{id:3}})).ok,false);
 assert.equal((await send({action:'TRANSFER',payload:{version:1}},{url:'https://evil.example/iol',tab:{id:3}})).ok,false);
 assert.equal((await send({action:'SELF_TEST',payload:{surgeon:'UNTRUSTED'}},{url:chrome.runtime.getURL('test.html')})).ok,true);
 assert.equal(records['1'].payload.surgeon,'CER-AI SYNTHETIC TEST');
 assert.equal(records['1'].payload.eyes.OD.toric,true);assert.equal(records['1'].payload.eyes.OS.toric,false);
 assert.equal(opened[0].url,'https://iolcalculator.escrs.org/');
 assert.equal((await send({action:'RECEIVE'},{url:'https://evil.example/',tab:{id:1}})).ok,false);
 assert(records['1']);assert.equal((await send({action:'RECEIVE'},{url:'https://iolcalculator.escrs.org/',tab:{id:2}})).ok,false);
 const result=await send({action:'RECEIVE'},{url:'https://iolcalculator.escrs.org/',tab:{id:1}});
 assert.equal(result.ok,true);assert.equal(result.payload.age,61);assert(!records['1']);
 assert.equal((await send({action:'RECEIVE'},{url:'https://iolcalculator.escrs.org/',tab:{id:1}})).ok,false);
 console.log('Message source and one-time tab-bound transfer tests passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
