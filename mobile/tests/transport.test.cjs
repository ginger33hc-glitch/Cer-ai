const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const t=require('../src/transport.cjs');
const message={channel:'CERAI_ESCRS_REQUEST',id:'test',action:'TRANSFER',payload:{version:1,eyes:{OD:{toric:true},OS:{toric:false}}}};
test('messages only accepted on exact HTTPS CER-AI IOL document',()=>{
 assert.deepEqual(t.parseRequest(JSON.stringify(message),'https://cer-ai.com/iol'),message);
 for(const url of ['http://cer-ai.com/iol','https://cer-ai.com.evil/iol','https://cer-ai.com/other','https://evil.example/iol','https://cer-ai.com:444/iol'])assert.equal(t.parseRequest(JSON.stringify(message),url),null);
 assert.equal(t.parseRequest('{bad','https://cer-ai.com/iol'),null);
 assert.equal(t.parseRequest(JSON.stringify({...message,payload:{version:1,eyes:{LEFT:{}}}}),'https://cer-ai.com/iol'),null);
});
test('mixed toric mode retained and payload cannot break script syntax',()=>{
 const payload={...message.payload,surgeon:"');globalThis.pwned=true;// </script>"};
 const script=t.transferScript('',payload,'test');let received;
 const context={location:{origin:'https://iolcalculator.escrs.org',pathname:'/'},window:{},CeraiEscrsAdapter:{run:p=>{received=p;return Promise.resolve();}},Promise};
 context.window.top=context.window;context.window.ReactNativeWebView={postMessage:()=>{}};
 vm.runInNewContext(script,context);
 return new Promise(resolve=>setImmediate(()=>{assert.equal(received.surgeon,payload.surgeon);assert.equal(received.eyes.OD.toric,true);assert.equal(received.eyes.OS.toric,false);assert.equal(context.pwned,undefined);resolve();}));
});
test('no injection on unrelated origins or embedded frames',()=>{
 for(const origin of ['https://evil.example','https://iolcalculator.escrs.org.evil']){
 const c={location:{origin,pathname:'/'},window:{},CeraiEscrsAdapter:{run:()=>{throw Error('must not run');}}};c.window.top=c.window;
 vm.runInNewContext(t.transferScript('',message.payload,'test'),c);assert.equal(c.window.__ceraiTransferRunning,undefined);
 }
});
test('mobile packages exactly the canonical adapter',()=>{
 const actual=fs.readFileSync(path.join(__dirname,'../src/adapter-source.js'),'utf8');
 const canonical=fs.readFileSync(path.join(__dirname,'../../extensions/escrs-assistant/adapter.js'),'utf8');
 assert.equal(actual.split('\n')[1],'export default '+JSON.stringify(canonical)+';');
});
