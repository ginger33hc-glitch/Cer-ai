"""Exercise transfer binding after results move outside the eye review panel."""
from pathlib import Path
import shutil
import subprocess

import pytest


def test_escrs_button_binds_in_moved_results_and_handles_transfer_failure():
    if not shutil.which("node"):
        pytest.skip("Node is not available")
    script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('static/iol.js', 'utf8');
const start = source.indexOf('      if(data.escrs_url)', source.indexOf('$("powerResult").innerHTML=html'));
const binding = source.slice(start, source.indexOf('      return true;', start));
(async () => {
  for (const eye of ['OD', 'OS']) {
    let click, destination, closed = false, fail = false;
    const button = {disabled:false, addEventListener:(event, handler) => {assert.equal(event, 'click'); click=handler;}};
    const result = {querySelector:selector => selector === `#${eye}-escrsTransfer` ? button : null};
    const status = {classList:{add:()=>{}}};
    const payload = {biological_sex:'Female', right_eye:{axial_length_mm:23}, left_eye:{axial_length_mm:24}};
    const target = 'https://iolcalculator.escrs.org/?biompin=test';
    const context = {
      eye, data:{escrs_url:target}, status,
      root:{querySelector:()=>null},
      $:id => id === 'powerResult' ? result : null,
      window:{open:()=>({opener:{}, location:{replace:url=>{destination=url;}}, close:()=>{closed=true;}})},
      escrsTransferPayload:()=>payload,
      errorMessage:body=>body.detail,
      fetch:async (url, options)=>{
        assert.equal(url, '/iol/escrs-transfer');
        assert.equal(options.credentials, 'same-origin');
        assert.deepEqual(JSON.parse(options.body), payload);
        return {ok:!fail, json:async()=>fail ? {detail:'Transfer unavailable'} : {escrs_url:target}};
      }
    };
    vm.runInNewContext(binding, context);
    assert.equal(typeof click, 'function');
    await click();
    assert.equal(destination, target);
    assert.equal(button.disabled, false);
    fail=true; destination=null;
    await click();
    assert.equal(destination, null);
    assert.equal(closed, true);
    assert.equal(status.textContent, 'Transfer unavailable');
    assert.equal(button.disabled, false);
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    subprocess.run(
        ["node", "-e", script], cwd=Path(__file__).resolve().parents[1],
        check=True, capture_output=True, text=True,
    )
