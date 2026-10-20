"""Pupil review changes eligibility only; explicit consent is eye-specific."""
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from test_iol_module import base_payload, power_payload
from iol_module.power import plan_iol_power


def case(pupil, confirmed=False, **assessment_changes):
    assessment = {**base_payload(), "eye": "OD", "pentacam_pupil_3d_mm": pupil,
                  "iolm500_k2_d": 42.5, "iolm500_k1_axis_deg": 20,
                  "iolm500_k2_axis_deg": 110, **assessment_changes}
    return power_payload(selected_lens_id="clareon-panoptix-cnwtt0",
                         clinical_assessment=assessment,
                         pupil_multifocal_confirmed=confirmed)


@pytest.mark.parametrize("pupil", [1.99, 4.01])
def test_multifocal_power_requires_explicit_confirmation(pupil):
    with patch("iol_module.power._call_k6") as calculate:
        with pytest.raises(ValueError, match="requires surgeon confirmation"):
            plan_iol_power(case(pupil))
        calculate.assert_not_called()


@pytest.mark.parametrize("pupil,confirmed", [(1.99, True), (4.01, True), (2.0, False), (4.0, False)])
def test_confirmed_and_boundary_values_continue_with_selected_lens(pupil, confirmed):
    with patch("iol_module.power._call_k6", return_value=[{"IOL": 20.0, "Rx": 0.0, "IsBestOption": True}]):
        plan = plan_iol_power(case(pupil, confirmed))
    assert plan.selected_lens_id == "clareon-panoptix-cnwtt0"
    assert plan.lens_category == "MULTIFOCAL"
    assert plan.inputs["pupil_multifocal_confirmed"] is confirmed
    assert plan.inputs["pentacam_pupil_3d_mm"] == pupil


@pytest.mark.parametrize("change", [{"macular_pathology_present": True}, {"glaucoma_status": "PRESENT"},
    {"total_corneal_hoa_4mm_um": .51}, {"ocular_surface_status": "MODERATE"},
    {"retina_status": "SIGNIFICANT"}, {"astigmatism_type": "IRREGULAR"}])
def test_confirmation_never_overrides_other_exclusions(change):
    with pytest.raises(ValueError, match="excluded by the clinical"):
        plan_iol_power(case(4.1, True, **change))


def test_confirmation_cannot_cross_eyes():
    with pytest.raises(ValueError, match="does not match"):
        plan_iol_power(case(4.1, True, eye="OS"))


def test_frontend_pupil_decision_filters_lenses_and_resets_selection():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/iol.js','utf8');
const start=source.indexOf('  function populateLenses()');
const fn=source.slice(start,source.indexOf('  function escrsEyePayload',start));
const choice={value:''},review={},select={innerHTML:''};
const ctx={recommendation:{eligible_categories:['MULTIFOCAL','EDOF','MONOFOCAL']},
 pupilReview:review,pupilChoice:choice,pupilReviewRequired:()=>true,
 lensCatalog:[{id:'mf',name:'MF',category:'MULTIFOCAL',a_constant:119},
 {id:'edof',name:'EDOF',category:'EDOF',a_constant:119}],$:()=>select};
vm.createContext(ctx);vm.runInContext(fn,ctx);
ctx.populateLenses();assert(!select.innerHTML.includes('value="mf"'));assert(!review.hidden);
choice.value='yes';ctx.populateLenses();assert(select.innerHTML.includes('value="mf"'));
choice.value='no';ctx.populateLenses();assert(!select.innerHTML.includes('value="mf"'));
assert(select.innerHTML.includes('value="edof"'));
ctx.pupilReviewRequired=()=>false;ctx.populateLenses();assert(review.hidden);
assert(select.innerHTML.includes('value="mf"'));
ctx.recommendation.eligible_categories=['EDOF'];choice.value='yes';ctx.populateLenses();
assert(!select.innerHTML.includes('value="mf"'));
assert(source.includes('assessmentPayload = null; pupilChoice.value = "";'));
assert(source.includes('clinical_assessment:assessmentPayload, pupil_multifocal_confirmed:pupilReviewRequired() && pupilChoice.value === "yes"'));
'''
    subprocess.run(["node", "-e", script], cwd=Path(__file__).resolve().parents[1], check=True)
