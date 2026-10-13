from pathlib import Path
import shutil
import subprocess

import pytest


def test_report_lifecycle_native_share_print_download_and_stale_results():
    if not shutil.which("node"):
        pytest.skip("Node not available")
    script = r'''
const assert = require('assert'), fs = require('fs'), vm = require('vm');
const nodes = new Map(), requests = [], revoked = [], downloads = [], shares = [], opened = [];
let sequence = 0, languageChanged, pageHandlers = {}, printCount = 0;
const getNode = id => {
  if (!nodes.has(id)) nodes.set(id, {hidden:false, disabled:true, handlers:{},
    classList:{toggle(){}}, addEventListener(event, handler){this.handlers[event]=handler;}});
  return nodes.get(id);
};
const document = {documentElement:{lang:'tr'}, getElementById:getNode,
  body:{appendChild(){}}, createElement:()=>({click(){downloads.push(this.href);},remove(){}})};
const window = {addEventListener:(name,fn)=>pageHandlers[name]=fn};
window.open = url => {opened.push(url);return {opener:{},addEventListener:(name,fn)=>fn(),focus(){},print(){printCount++;}};};
const navigator = {canShare:()=>true,share:async value=>{shares.push(value);}};
const context = {document, window, navigator, console, AbortController,
  File:class {constructor(parts,name,opts){this.name=name;this.type=opts.type;}},
  URL:{createObjectURL:()=>`blob:${++sequence}`,revokeObjectURL:value=>revoked.push(value)},
  MutationObserver:class {constructor(fn){languageChanged=fn;}observe(){}},
  fetch:(url,options)=>new Promise(resolve=>requests.push({url,options,resolve}))};
vm.runInNewContext(fs.readFileSync('static/iol-report.js','utf8'),context);
const setCase = window.CERAI_IOL_REPORT.setCase;
const flush = () => new Promise(resolve=>setImmediate(resolve));
const complete = request => request.resolve({ok:true,headers:{get:()=> 'application/pdf'},blob:async()=>({})});
(async()=>{
  const first = {patient_name:'A',eyes:[{eye:'OD'}]};
  setCase(first);
  assert.equal(requests.length,1); assert.equal(getNode('iolReportShare').disabled,true);
  assert.equal(JSON.parse(requests[0].options.body).locale,'tr');
  setCase(null); assert.equal(getNode('iolReportSection').hidden,true);
  complete(requests[0]); await flush(); assert.equal(sequence,0); // stale response discarded
  setCase(first); complete(requests[1]); await flush();
  assert.equal(getNode('iolReportShare').disabled,false);
  setCase(first); assert.equal(requests.length,2); // no duplicate fetch
  await getNode('iolReportShare').handlers.click(); assert.equal(shares.length,1);
  assert.equal(shares[0].files[0].type,'application/pdf');
  getNode('iolReportPrint').handlers.click(); assert.equal(printCount,1); assert.equal(opened[0],'blob:1');
  navigator.canShare=()=>false;
  await getNode('iolReportShare').handlers.click(); assert.deepEqual(downloads,['blob:1']);
  document.documentElement.lang='en'; languageChanged();
  assert.deepEqual(revoked,['blob:1']); assert.equal(getNode('iolReportShare').disabled,true);
  assert.equal(JSON.parse(requests[2].options.body).locale,'en');
  requests[2].resolve({ok:false}); await flush(); assert.equal(getNode('iolReportRetry').hidden,false);
  getNode('iolReportRetry').handlers.click(); complete(requests[3]); await flush();
  assert.equal(getNode('iolReportShare').disabled,false);
  pageHandlers.pagehide(); assert.equal(getNode('iolReportShare').disabled,true);
  pageHandlers.pageshow({persisted:true}); assert.equal(requests.length,5);
  setCase(null); complete(requests[4]); await flush(); assert.equal(sequence,2);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    # Keep harness independent of a browser / native share dialog.
    subprocess.run(["node", "-e", script], cwd=Path(__file__).resolve().parents[1],
                   check=True, capture_output=True, text=True)
