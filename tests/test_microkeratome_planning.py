import pytest
from clinical_core.disposition import STOP_DEFER, ASSESSMENT_INCOMPLETE

from planning.microkeratome import MicrokeratomePlanningInput, plan_microkeratome


def base(**kw):
    data = dict(assessment_status="PASS", procedure="LASIK", steepest_k_d=44.0,
                flattest_k_d=42.0, w2w_mm=11.2, pachy_um=540, t_zone_mm=8.0,
                planned_flap_um=100, max_ablation_um=60)
    data.update(kw)
    return MicrokeratomePlanningInput(**data)


def test_module_is_available_after_pass_or_non_deferring_caution():
    assert plan_microkeratome(base(assessment_status="CAUTION")).applicable
    assert not plan_microkeratome(base(procedure="PRK")).applicable


def test_pass_is_an_active_favorable_gate():
    plan = plan_microkeratome(base(assessment_status="PASS"))
    assert plan.applicable
    assert plan.assessment_gate == "PASS"


def test_nomogram_mid_range_small_cornea():
    p = plan_microkeratome(base())
    assert p.vacuum_ring_mm == 8.5
    assert p.vacuum_pressure_mmhg == "550"
    assert p.ring_tzone_clearance_mm == 0.5


def test_k_point_50_rounds_up():
    p = plan_microkeratome(base(steepest_k_d=46.5, flattest_k_d=44.0))
    assert p.vacuum_ring_mm == 8.0


def test_large_w2w_changes_ring():
    p = plan_microkeratome(base(w2w_mm=11.5))
    assert p.vacuum_ring_mm == 9.0


def test_missing_horizontal_wtw_blocks_ring_recommendation():
    p = plan_microkeratome(base(w2w_mm=None))
    assert p.vacuum_ring_mm is None
    assert p.vacuum_pressure_mmhg is None
    assert any("horizontal white-to-white (HWTW)" in warning for warning in p.warnings)


def test_delta_k_strictly_over_four_maps_horizontal_meridian_to_temporal_hinge():
    p = plan_microkeratome(base(steepest_k_d=46.1, flattest_k_d=42.0, steep_axis_deg=20))
    assert p.delta_k_d == 4.1
    assert "Temporal hinge preferred" in p.primary_hinge
    assert p.steep_meridian_axis_deg == 20
    assert p.hinge_location_preference == "Temporal"
    assert p.hinge_location_alternative == "Nasal"


@pytest.mark.parametrize("steep_axis", [60, 90, 120])
def test_vertical_steep_meridian_prefers_superior_hinge(steep_axis):
    p = plan_microkeratome(base(steepest_k_d=46.1, flattest_k_d=42.0, steep_axis_deg=steep_axis))
    assert p.steep_meridian_axis_deg == pytest.approx(steep_axis, abs=0.1)
    assert p.hinge_location_preference == "Superior"
    assert p.hinge_location_alternative is None
    assert "Superior hinge at the vertical steep meridian" in p.primary_hinge


@pytest.mark.parametrize("steep_axis", [0, 30, 150, 180])
def test_horizontal_steep_meridian_prefers_temporal_hinge(steep_axis):
    p = plan_microkeratome(base(steepest_k_d=46.1, flattest_k_d=42.0, steep_axis_deg=steep_axis))
    assert p.steep_meridian_axis_deg == pytest.approx(steep_axis % 180, abs=0.1)
    assert p.hinge_location_preference == "Temporal"
    assert p.hinge_location_alternative == "Nasal"
    assert "Temporal hinge preferred at the horizontal steep meridian" in p.primary_hinge


@pytest.mark.parametrize("steep_axis", [30.01, 45, 59.99, 120.01, 135, 149.99])
def test_oblique_high_astigmatism_retains_temporal_default(steep_axis):
    p = plan_microkeratome(base(steepest_k_d=46.1, flattest_k_d=42.0, steep_axis_deg=steep_axis))
    assert p.steep_meridian_axis_deg == pytest.approx(steep_axis, abs=0.1)
    assert p.hinge_location_preference == "Temporal"
    assert p.hinge_location_alternative is None
    assert "Temporal hinge remains the default" in p.primary_hinge
    assert "requires surgeon judgment" in p.primary_hinge


def test_delta_k_exact_four_does_not_trigger_hc_rule():
    p = plan_microkeratome(base(steepest_k_d=46.0, flattest_k_d=42.0))
    assert p.delta_k_d == 4.0
    assert p.primary_hinge == "Temporal hinge (default)"
    assert p.steep_meridian_axis_deg is None
    assert p.hinge_location_preference == "Temporal"


def test_temporal_is_default_when_delta_k_or_axis_is_unavailable():
    missing_k = plan_microkeratome(base(steepest_k_d=None, flattest_k_d=None))
    assert missing_k.primary_hinge == "Temporal hinge (default)"
    assert missing_k.hinge_location_preference == "Temporal"

    missing_axis = plan_microkeratome(base(
        steepest_k_d=47, flattest_k_d=42, steep_axis_deg=None,
    ))
    assert missing_axis.primary_hinge == "Temporal hinge (default)"
    assert missing_axis.hinge_location_preference == "Temporal"
    assert any("temporal remains the default" in warning for warning in missing_axis.warnings)


def test_anatomic_exception_requires_rsb_pta_clearance():
    blocked = plan_microkeratome(base(steepest_k_d=47, flattest_k_d=42,
        pachy_um=480, planned_flap_um=100, max_ablation_um=80,
        steep_axis_deg=90, superior_hinge_anatomically_possible=False))
    assert blocked.alternative_hinge is None
    assert blocked.alternative_safety == "NOT_ALLOWED"
    allowed = plan_microkeratome(base(steepest_k_d=47, flattest_k_d=42,
        steep_axis_deg=90, superior_hinge_anatomically_possible=False))
    assert allowed.alternative_hinge == "+10 blade; temporal or nasal hinge"
    assert allowed.alternative_rsb_um == 370
    assert allowed.alternative_pta_percent == pytest.approx(31.481, abs=0.001)


def test_unknown_anatomy_exposes_only_a_conditional_safe_alternative():
    plan = plan_microkeratome(base(steepest_k_d=47, flattest_k_d=42, steep_axis_deg=90))
    assert plan.primary_hinge == "Superior hinge at the vertical steep meridian (90°)"
    assert plan.alternative_hinge == "+10 blade; temporal or nasal hinge"
    assert any("only if the surgeon determines" in note for note in plan.notes)


def test_plus_ten_alternative_uses_inclusive_rsb_and_exclusive_pta_boundaries():
    rsb_boundary = plan_microkeratome(base(
        steepest_k_d=47, flattest_k_d=42, pachy_um=490,
        planned_flap_um=100, max_ablation_um=80, steep_axis_deg=90,
    ))
    assert rsb_boundary.alternative_rsb_um == 300
    assert rsb_boundary.alternative_safety == "ALLOWED"

    pta_boundary = plan_microkeratome(base(
        steepest_k_d=47, flattest_k_d=42, pachy_um=500,
        planned_flap_um=100, max_ablation_um=90, steep_axis_deg=90,
    ))
    assert pta_boundary.alternative_pta_percent == 40.0
    assert pta_boundary.alternative_safety == "NOT_ALLOWED"


def test_horizontal_primary_hinge_does_not_offer_superior_hinge_contingency():
    plan = plan_microkeratome(base(
        steepest_k_d=47, flattest_k_d=42, steep_axis_deg=0,
        superior_hinge_anatomically_possible=False,
    ))
    assert plan.hinge_location_preference == "Temporal"
    assert plan.alternative_hinge is None
    assert plan.alternative_safety == "NOT_APPLICABLE"


def test_manual_blade_rules_can_coexist_and_are_not_silently_resolved():
    p = plan_microkeratome(base(steepest_k_d=39, flattest_k_d=37, pachy_um=500))
    assert "-10 blade" in p.blade_recommendations
    assert "+10 blade" in p.blade_recommendations
    assert "+20 blade" in p.blade_recommendations


def test_hyperopic_low_hinge_k_rule():
    p = plan_microkeratome(base(hyperopic=True, hinge_site_lowest_k_d=37))
    assert "+10 blade" in p.blade_recommendations
    assert any("hinge-site lowest K" in n for n in p.notes)


@pytest.mark.parametrize('axis', [0, 20, 45, 59.9, 90, 135, 180])
@pytest.mark.parametrize('spread', [0.5, 4, 5])
@pytest.mark.parametrize('status', ['PASS', STOP_DEFER, ASSESSMENT_INCOMPLETE])
def test_hyperopic_hinge_always_uses_exact_steep_axis(axis, spread, status):
    plan = plan_microkeratome(base(hyperopic=True, steep_axis_deg=axis,
        steepest_k_d=42+spread, assessment_status=status,
        superior_hinge_anatomically_possible=False))
    assert plan.steep_meridian_axis_deg == axis % 180
    assert plan.primary_hinge == f'Mandatory steep-axis hinge ({axis % 180:g}°)'
    assert plan.hinge_location_preference == plan.primary_hinge
    assert plan.alternative_hinge is None
    assert plan.hinge_location_alternative is None
    assert plan.assessment_gate == status


@pytest.mark.parametrize('axis', [None, -1, 181, float('nan'), float('inf'), True])
def test_hyperopic_missing_or_invalid_axis_never_defaults_temporal(axis):
    plan = plan_microkeratome(base(hyperopic=True, steep_axis_deg=axis))
    assert plan.steep_meridian_axis_deg is None
    assert plan.hinge_location_preference is None
    assert 'confirm' in plan.primary_hinge
    assert any('enter or confirm' in w for w in plan.warnings)
    assert plan.vacuum_ring_mm == 8.5


def test_hyperopic_low_k_cannot_offer_off_axis_hinge():
    plan = plan_microkeratome(base(hyperopic=True, steep_axis_deg=90,
        hinge_site_lowest_k_d=37))
    assert not any('higher-K temporal/nasal' in n for n in plan.notes)
    assert plan.alternative_hinge is None


def test_runtime_uses_canonical_k2_axis_for_hyperopic_lasik():
    from canonical_runtime_service import _microkeratome_planning
    from clinical_core.refraction import HYPEROPIC
    result = _microkeratome_planning(
        {'K1_D': 42, 'K2_D': 43, 'K2_axis_deg': 73, 'pachy_thinnest_um': 540},
        {'procedure': 'LASIK', 'flap_um': 100, 'ablation_um': 60},
        {'status': STOP_DEFER, 'intended_refractive_group': HYPEROPIC},
    )
    assert result['primary_hinge'] == 'Mandatory steep-axis hinge (73°)'
    assert result['assessment_gate'] == STOP_DEFER


def test_hyperopic_hinge_turkish_translation():
    from cerai_i18n import translate_text
    assert translate_text('Mandatory steep-axis hinge (73°)', 'tr') == 'Dik aksta zorunlu menteşe (73°)'
    plan = plan_microkeratome(base(hyperopic=True))
    assert 'doğrulayın' in translate_text(plan.primary_hinge, 'tr')
    warning = next(w for w in plan.warnings if 'Hyperopic LASIK' in w)
    assert 'Hipermetropik LASIK' in translate_text(warning, 'tr')
