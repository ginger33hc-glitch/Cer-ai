from io import BytesIO
from unittest.mock import patch
import json
import pytest
from iol_module.models import IOLPowerPlanInput
from iol_module.power import plan_iol_power

def power_payload(**overrides):
    payload = {
        "patient_name": "Test Patient", "biological_sex": "Female", "eye": "OD",
        "selected_lens_id": "clareon-mono-sy60wf", "axial_length_mm": 24.2,
        "acd_mm": 2.21, "k1_d": 42.0, "k1_axis_deg": 20,
        "k2_d": 42.5, "k2_axis_deg": 110, "astigmatism_type": None,
        "prior_corneal_surgery": "NONE",
        "historical_data_available": False, "incision_axis_deg": None,
        "sia_d": None, "sia_axis_deg": None, "cct_um": 573,
        "lens_thickness_mm": None, "wtw_mm": 11.7,
    }
    payload.update(overrides)
    return IOLPowerPlanInput.model_validate(payload)

@pytest.mark.parametrize('status,body,required', [
    (422, b'{"LT":"required"}', True),
    (400, b'Lens thickness is mandatory', True),
    (422, b'Invalid measurements', False),
    (422, b'LT is not required', False),
    (429, b'LT required', False),
])
def test_only_explicit_k6_validation_requests_lt(status, body, required):
    from urllib.error import HTTPError
    failure = HTTPError('https://example.invalid', status, 'Rejected', {}, BytesIO(body))
    with patch('iol_module.power.urlopen', side_effect=failure):
        plan = plan_iol_power(power_payload(lens_thickness_mm=None))
    assert plan.required_inputs == (['lens_thickness_mm'] if required else [])
    if status == 429:
        assert 'request limit' in plan.fallback_reason
    assert bool(plan.predictions) == (status == 429)


@pytest.mark.parametrize('lt', [None, 4.5])
def test_short_eye_sends_only_measured_lt(lt):
    response = b'[{"IOLs":[{"Predictions":[{"IOL":28,"Rx":0,"IsBestOption":true}]}]}]'
    with patch('iol_module.power.urlopen', return_value=BytesIO(response)) as call:
        plan = plan_iol_power(power_payload(axial_length_mm=20.45, lens_thickness_mm=lt))
    assert plan.calculation_status == 'COMPLETED'
    eye = json.loads(call.call_args.args[0].data)['Eyes'][0]
    assert ('LT' in eye) == (lt is not None)
    assert plan.required_inputs == []
