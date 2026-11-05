import pytest
from test_canonical_runtime_service import _evaluate, _plan, _case, _eye


def smile(**kw):
    return _plan('SMILE', smile_cap_um=120, optical_zone_mm=6.5,
                 laser_platform='ZEISS_VISUMAX_800', **kw)


@pytest.mark.parametrize('cylinder', [0, -1, -5])
def test_missing_device_never_passes(cylinder):
    result = _evaluate(plans={'OD': smile(intended_cylinder_signed_D=cylinder), 'OS': _plan()})
    eye = result['eyes'][0]
    assert eye['status'] not in {'PASS', 'PASS WITH CAUTION'}
    assert any('smile_device_max_lenticule_um' in item for item in eye['missing'])
    assert result['eyes'][1]['status'] == 'PASS'


@pytest.mark.parametrize('lt', [None, 0, -1, float('nan')])
def test_invalid_device_value_remains_incomplete(lt):
    eye = _evaluate(plans={'OD': smile(max_lenticule_thickness_um=lt), 'OS': _plan()})['eyes'][0]
    assert any('smile_device_max_lenticule_um' in item for item in eye['missing'])


@pytest.mark.parametrize('platform', ['ZEISS_VISUMAX_500', 'ZEISS_VISUMAX_800'])
def test_device_recalculation_and_stop_precedence(platform):
    plan = smile(max_lenticule_thickness_um=70)
    plan['laser_platform'] = platform
    safe = _evaluate(plans={'OD': plan, 'OS': _plan()})['eyes'][0]
    assert safe['values']['SMILE_RSB_um'] == 355
    plan['max_lenticule_thickness_um'] = 98
    stopped = _evaluate(plans={'OD': plan, 'OS': _plan()})['eyes'][0]
    assert stopped['status'] == 'STOP-DEFER'  # exactly 40%, unchanged institutional gate
    assert stopped['values']['SMILE_PTA_percent'] == 40


def test_missing_device_does_not_mask_independent_stop():
    eye = _evaluate(extracted=_case(od=_eye(BAD_D=3)),
                    plans={'OD': smile(), 'OS': _plan()})['eyes'][0]
    assert eye['status'] == 'STOP-DEFER'
    assert any('smile_device_max_lenticule_um' in item for item in eye['missing'])

@pytest.mark.parametrize('lt', [97.9, 98, 98.1, 124.9, 125, 125.1])
def test_tissue_boundaries_unchanged(lt):
    eye = _evaluate(plans={'OD': smile(max_lenticule_thickness_um=lt), 'OS': _plan()})['eyes'][0]
    assert eye['values']['SMILE_RSB_um'] == pytest.approx(425-lt)
    assert eye['values']['SMILE_PTA_percent'] == pytest.approx(100*(120+lt)/545)
    if lt >= 98:
        assert eye['status'] == 'STOP-DEFER'


def test_estimate_never_becomes_device_source_and_cylinder_has_no_estimate():
    for cyl in [0, -5]:
        plan = smile(intended_cylinder_signed_D=cyl)
        eye = _evaluate(plans={'OD': plan, 'OS': _plan()})['eyes'][0]
        selected = eye['report_payload']['planning']['selected_procedure_plan']
        assert selected['max_lenticule_thickness_um'] is None
        assert selected['lenticule_source'] == 'DEVICE_MAXIMUM_REQUIRED'
        assert (selected['estimated_lenticule_thickness_um'] is None) == (cyl != 0)
    plan = smile(max_lenticule_thickness_um=60, lenticule_source='CERAI_THEORETICAL_MYOPIC_SMILE_ESTIMATE')
    assert _evaluate(plans={'OD': plan, 'OS': _plan()})['eyes'][0]['status'] == 'ASSESSMENT INCOMPLETE'


def test_missing_device_completion_maps_to_correct_eye_input():
    from assessment_workflow import _request
    for eye in ['OD', 'OS']:
        extracted = {'_effective_eye_plans': {eye: smile()}}
        for missing in ['Safety: smile_device_max_lenticule_um', 'Safety: ablation_um', 'Randleman: rsb']:
            req = _request(eye, missing, extracted)
            assert req['key'] == 'max_lenticule_thickness_um'
            assert req['form_id'] == eye.lower() + '_lenticule'


def test_smile_report_translations():
    from cerai_i18n import translate_text
    from reports import _selected_procedure_summary
    eye = _evaluate(plans={'OD': smile(max_lenticule_thickness_um=70, intended_cylinder_signed_D=0), 'OS': _plan()})['eyes'][0]
    label, details = _selected_procedure_summary(eye['report_payload']['planning'])
    assert 'SURGEON_ENTERED_VISUMAX_MAXIMUM' in details
    assert 'Estimated LT (preliminary only)' in details
    assert 'VisuMax ekranından' in translate_text(details, 'tr')
    assert translate_text('smile_device_max_lenticule_um', 'tr') != 'smile_device_max_lenticule_um'
