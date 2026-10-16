"""BiomDIRECT field contracts: no loss, swapping, or inference of clinical data."""
import pytest
from pydantic import ValidationError
from iol_module.models import EscrsTransferInput
from iol_module.escrs_transfer import build_biomdirect


def eye(**updates):
    return dict(axial_length_mm=23.5, acd_mm=3.1, k1_d=42.5, k2_d=44,
                **updates)


def test_bilateral_axes_history_and_missing_measurements_are_preserved():
    case = EscrsTransferInput(biological_sex='Female',
        right_eye=eye(k1_axis_deg=15, k2_axis_deg=105, cct_um=550,
                      lens_thickness_mm=4.3, prior_corneal_surgery='MYOPIC_LASIK_PRK'),
        left_eye=eye(k1_axis_deg=170, k2_axis_deg=80, prior_corneal_surgery='NONE'))
    data = build_biomdirect(case)['data']
    assert (data['right_eye']['K1_axis'], data['right_eye']['K2_axis']) == (15,105)
    assert (data['left_eye']['K1_axis'], data['left_eye']['K2_axis']) == (170,80)
    assert data['right_eye']['post_refractive'] == 'Myopic LVC'
    assert data['left_eye']['post_refractive'] == 'None'
    assert data['right_eye']['CCT'] == 550 and type(data['right_eye']['CCT']) is int
    assert 'LT' not in data['left_eye']
    assert 'CCT' not in data['left_eye']


@pytest.mark.parametrize('fields', [dict(k1_axis_deg=15.2),
    dict(k1_axis_deg=15,k2_axis_deg=104), dict(cct_um=550.5)])
def test_invalid_integer_schema_values_are_not_silently_changed(fields):
    with pytest.raises(ValidationError):
        EscrsTransferInput(biological_sex='Male',right_eye=eye(**fields))


def test_absent_axes_and_history_are_not_inferred():
    data = build_biomdirect(EscrsTransferInput(biological_sex='Male',right_eye=eye()))['data']
    assert data['left_eye'] == {}
    assert 'K1_axis' not in data['right_eye'] and 'K2_axis' not in data['right_eye']
    assert 'post_refractive' not in data['right_eye']
