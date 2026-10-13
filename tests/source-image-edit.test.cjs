const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const listeners=[];
const input={files:[],addEventListener:(_,fn)=>listeners.push(fn),closest:()=>null,parentElement:null,dispatchEvent(event){for(const fn of listeners)fn(event);}};
class DataTransfer{constructor(){this.files=[];this.items={add:file=>this.files.push(file)};}}
const context={window:{},document:{getElementById:id=>id==='imageInput'?input:null,querySelectorAll:()=>[]},DataTransfer,Event,queueMicrotask};
vm.runInNewContext(fs.readFileSync('static/assessment-readiness.js','utf8'),context);
const api=context.window.CER_AI_SourceImageRetention;
const a={name:'OD.jpg',size:1,lastModified:1},b={name:'OS.jpg',size:2,lastModified:1},c={name:'new.jpg',size:3,lastModified:1};
api.adopt([a,b]);
api.replaceAll([b]);assert.deepEqual(input.files,[b]);
input.files=[c];input.dispatchEvent(new Event('change'));assert.deepEqual(input.files,[b,c]);
api.replaceAll([a,c]);assert.deepEqual(input.files,[a,c]);
api.replaceAll([]);assert.deepEqual(input.files,[]);assert.equal(api.files().length,0);
input.files=[b];input.dispatchEvent(new Event('change'));assert.deepEqual(input.files,[b]);
console.log('Image removal, replacement, add-after-remove and empty-list checks passed');
