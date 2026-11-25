"""Regression for the removed UI questionnaire blocking report completion."""
import pytest
from test_step11_analyze_completion_workflow import _respond, _plan, _eye
from canonical_runtime_service import evaluate_case


@pytest.mark.parametrize('procedure', ['LASIK', 'PRK', 'SMILE'])
@pytest.mark.parametrize('modifiers', [{}, {'contact_lens_type': 'UNKNOWN'}, {'dry_eye': 'unknown'}])
def test_current_ui_payload_completes_without_questionnaire(procedure, modifiers):
    plan = _plan(prior='unknown', procedure=procedure)
    for key in ('stable', 'progression', 'cdva_below_20_20'):
        plan.pop(key)
    if procedure == 'SMILE':
        plan.update(smile_cap_um=120, max_lenticule_thickness_um=60,
                    lenticule_source='SURGEON_ENTERED_VISUMAX_MAXIMUM', optical_zone_mm=6.5)
    response = _respond(plans={'OD': plan, 'OS': dict(plan)}, modifiers=modifiers)
    assert response['workflow_status'] == 'READY'
    assert response['report_token']
    assert not response.get('input_requests')
    assert all(eye['status'] != 'ASSESSMENT INCOMPLETE' for eye in response['decision']['eyes'])


def test_missing_actual_measurement_still_requests_completion():
    response = _respond(od=_eye('OD', I_S=None), modifiers={'contact_lens_type': 'UNKNOWN'})
    assert response['workflow_status'] == 'NEEDS_INPUT'
    assert response['report_token'] is None
    assert any(item['key'] == 'I_S' for item in response['input_requests'])
    assert all('contact_lens' not in item['key'] for item in response['input_requests'])


def test_measured_stop_is_preserved_without_questionnaire():
    response = _respond(od=_eye('OD', BAD_D=3.0), modifiers={'contact_lens_type': 'UNKNOWN'})
    assert response['decision']['eyes'][0]['status'] == 'STOP-DEFER'


def test_omitted_modifiers_and_unverified_prior_do_not_generate_missing_findings():
    plan = _plan(prior='unknown')
    for key in ('stable', 'progression', 'cdva_below_20_20'):
        plan.pop(key)
    result = evaluate_case({'eyes': [_eye('OD'), _eye('OS')]}, 35,
                           {'OD': plan, 'OS': dict(plan)})
    assert result['status'] == 'PASS'
    assert all(not eye['missing'] for eye in result['eyes'])
