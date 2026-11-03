"""Exercise actual browser helpers without network or patient data."""
from pathlib import Path
import subprocess


def test_axis_review_and_transfer_preserve_surgeon_corrections():
    source = (Path(__file__).resolve().parents[1] / 'static/iol.js').read_text()
    review = source[source.index('  function markAxisPair('):source.index('  function populateEye()')]
    transfer = source[source.index('  function escrsTransferPayload()'):source.index('  function posteriorAxesConflict(')]
    script = '''
const assert = require('node:assert/strict');
const fields = {k1:43.10,k2:44.53,k1Axis:14,k2Axis:104};
const flags = {};
const requiresRegularity = d => d > 1;
const $ = id => ({id, value:id === 'biologicalSex' ? 'Male' : fields[id],
 classList:{toggle:(name,value)=>{flags[id]=value;}},setAttribute:()=>{}});
const numberOrNull = id => fields[id] ?? null;
const tr = x => x;
let focused;
const revealRequiredField = field => focused = field.id;
''' + review + transfer + '''
assert.equal(reviewKeratometry(true),true);
assert.equal(fields.k2Axis,104);
fields.k2Axis=14;
assert.equal(reviewKeratometry(true),false);
assert.equal(focused,'k2Axis');
assert.equal(flags.k1Axis,true); assert.equal(flags.k2Axis,true);
assert.equal(fields.k2Axis,14); // never silently rotate the source
const loadedEyes=['OS'];
const controllers=new Map([['OS',{reviewKeratometry,transferMeasurements:()=>({...fields})}]]);
assert.throws(escrsTransferPayload,/OS:/);
fields.k2Axis=104;
assert.equal(escrsTransferPayload().left_eye.k2Axis,104);
assert.equal(flags.k1Axis,false); assert.equal(flags.k2Axis,false);
assert.equal(escrsTransferPayload().right_eye,null);
fields.k2Axis=103;
assert.equal(reviewKeratometry(),true);
assert.equal(reviewKeratometry(true),false);
fields.k1Axis=0;fields.k2Axis=90;
assert.equal(reviewKeratometry(true),true);
fields.k1Axis=180;
assert.equal(reviewKeratometry(true),true);
fields.k1Axis=null;
assert.equal(reviewKeratometry(true),false);
fields.k1Axis=14.5;fields.k2Axis=104.5;
assert.equal(reviewKeratometry(true),false);
'''
    subprocess.run(['node', '-e', script], check=True)
