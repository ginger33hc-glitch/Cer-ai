"""Published numerical references and K6/T2 route regressions."""
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import pytest
from iol_module.t2 import predicted_refraction, predictions
from iol_module.power import plan_iol_power
from test_k6_service_contract import power_payload


@pytest.mark.parametrize('failure', [TimeoutError(), URLError('offline'), HTTPError('https://example.invalid', 429, 'limit', {}, None), HTTPError('https://example.invalid', 503, 'unavailable', {}, None), HTTPError('https://example.invalid', 404, 'unavailable', {}, None)])
@pytest.mark.parametrize('eye', ['OD', 'OS'])
def test_outage_calculates_locally_without_lt(failure, eye):
    with patch('iol_module.power.urlopen', side_effect=failure) as request:
        plan = plan_iol_power(power_payload(eye=eye))
    assert request.call_count == 1
    assert plan.route == 'T2'
    assert plan.spherical_formula == 'T2'
    assert plan.calculator_name == 'T2'
    assert plan.calculation_status == 'COMPLETED'
    assert plan.required_inputs == []
    assert 'lens_thickness_mm' not in plan.inputs
    assert plan.escrs_url
    best = [p for p in plan.predictions if p['IsBestOption']]
    assert len(best) == 1
    assert abs(best[0]['Rx'] - plan.target_refraction_d) == min(abs(p['Rx'] - plan.target_refraction_d) for p in plan.predictions)


def test_k6_success_never_calls_t2():
    with patch('iol_module.power._call_k6', return_value=[{'IOL': 21, 'Rx': 0, 'IsBestOption': True}]), patch('iol_module.power.t2_predictions') as t2:
        plan = plan_iol_power(power_payload())
    t2.assert_not_called()
    assert plan.spherical_formula == 'Cooke K6'
    assert plan.fallback_reason is None


@pytest.mark.parametrize('surgery', ['MYOPIC_LASIK_PRK', 'HYPEROPIC_LASIK_PRK', 'RK'])
def test_post_refractive_never_uses_standard_formulas(surgery):
    with patch('iol_module.power._call_k6') as k6, patch('iol_module.power.t2_predictions') as t2:
        plan = plan_iol_power(power_payload(prior_corneal_surgery=surgery))
    k6.assert_not_called()
    t2.assert_not_called()
    assert not plan.predictions


def test_t2_toric_spherical_anchor_and_identity():
    case = power_payload(selected_lens_id='clareon-panoptix-toric-cnwtt3',
        k2_d=43.25, astigmatism_type='REGULAR', incision_axis_deg=110,
        sia_d=0.25, sia_axis_deg=110,
        posterior_cornea={'eye': 'OD', 'source': 'PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK',
                          'k1_d': -5.8, 'k2_d': -6.1, 'k2_axis_deg': 110})
    with patch('iol_module.power._call_k6', side_effect=TimeoutError()):
        plan = plan_iol_power(case)
    assert plan.spherical_formula == 'T2'
    assert plan.calculator_name == 'T2 spherical power'
    assert plan.toric_status == 'TEST_ONLY'
    best = next(p for p in plan.predictions if p['IsBestOption'])
    assert plan.toric_candidates
    assert all(p['spherical_equivalent_iol_d'] == best['IOL'] for p in plan.toric_candidates)


def test_out_of_range_does_not_fabricate_a_best_power():
    with pytest.raises(ValueError, match='outside'):
        predictions(20, 40, 40, 119, 0)
    with patch('iol_module.power._call_k6', side_effect=TimeoutError()):
        plan = plan_iol_power(power_payload(axial_length_mm=20, k1_d=40, k2_d=40))
    assert plan.calculation_status == 'CALCULATION_UNAVAILABLE'
    assert not plan.predictions
    assert plan.escrs_url


@pytest.mark.parametrize('args', [(24,31,42,119,20),(24,42,58,119,20),(24,42,42,float('nan'),20)])
def test_published_limits(args):
    with pytest.raises(ValueError):
        predicted_refraction(*args)

# Reference outputs from upstream test-formula.test.ts, pinned in t2.py.
@pytest.mark.parametrize("expected,al,k1,k2,a,power", [
    (-0.511022750699568, 23.600300773978233, 44.082986036548014, 44.159396314530696, 119.0, 21.0),
    (-1.2796886178027, 23.589400574564934, 44.11776282715324, 44.38139930062693, 119.0, 22.0),
    (-0.792915256128844, 23.930100724101067, 41.21011413373744, 42.48884388734912, 119.0, 23.0),
    (-1.99557935807807, 23.99853989481926, 41.64827560660122, 42.85517229555152, 119.0, 24.0),
    (-13.7799162341546, 27.00739912688732, 45.95402887494731, 47.09208890744176, 119.0, 25.0),
    (-13.9063115373869, 26.955800130963326, 45.22839650482536, 46.57650834119935, 119.0, 26.0),
    (-4.68608228175599, 24.7770007699728, 40.13689830901598, 41.11188063320193, 119.0, 27.0),
    (-5.7490864331149, 24.760720506310463, 40.2961224272421, 41.5951259787359, 119.0, 28.0),
    (-8.41717196138769, 26.078380271792412, 39.34842412695875, 39.985148251959664, 119.0, 29.0),
    (-8.61931407335799, 25.680160149931908, 39.58341042138732, 40.14249625867187, 119.0, 30.0),
    (-18.4247731392868, 30.81749938428402, 42.46266293625579, 45.12782295103, 119.0, 24.5),
    (3.34622781528607, 20.291699096560478, 43.765035968692324, 44.46927085082063, 119.0, 27.5),
])
def test_published_numerical_examples(expected,al,k1,k2,a,power):
    assert predicted_refraction(al,k1,k2,a,power) == pytest.approx(expected, abs=1e-10)
