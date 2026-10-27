"""Exercise the actual browser population function with both-eye source conflicts."""
import json
import subprocess
from pathlib import Path


def test_iolmaster_acd_wins_for_each_eye_and_missing_stays_missing():
    source = Path("static/iol.js").read_text()
    function = source[source.index("  function populateEye() {"):source.index('  $("incisionAxis").addEventListener')]
    helper = source[source.index("  function posteriorAxesConflict"):source.index("  function syncWorkflow")]
    script = helper + """
const assert = require('node:assert/strict');
const fields = {};
const $ = id => fields[id] ||= {value: '', readOnly: false};
const setIfPresent = (id, value) => { if (value !== null && value !== undefined) $(id).value = value; };
const originals = {OD: {acd_mm: 3.2}, OS: {acd_mm: 2.8}};
const pentacamByEye = {OD: {acd_internal_mm: 2.6}, OS: {acd_internal_mm: 2.2}};
const corneaBackByEye = {};
const posteriorFields = [];
const updateAstigmatism = () => {};
""" + function + """
$('eye').value = 'OD'; populateEye();
assert.equal($('acd').value, 3.2);
$('eye').value = 'OS'; populateEye();
assert.equal($('acd').value, 2.8);
originals.OS.acd_mm = null; populateEye();
assert.equal($('acd').value, '');
assert.equal($('acd').readOnly, false);
"""
    subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
