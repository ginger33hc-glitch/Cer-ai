"""Actual maximum ablation belongs to the matching LASIK treatment zones."""
import pytest

from test_step9_planning_runtime_acceptance import _evaluate, _plan


@pytest.mark.parametrize("zones", [
    {"transition_zone_mm": 8.5},
    {"transition_zone_mm": 9.0},
    {"optical_zone_mm": 6.5},
])
def test_partial_zones_cannot_assign_actual_hyperopic_ablation_to_plan_a(zones):
    _, eyes = _evaluate(od_plan=_plan(
        ablation_um=70.0,
        intended_entered_sphere_D=2.0,
        intended_cylinder_signed_D=0.0,
        **zones,
    ))
    planning = eyes["OD"]["planning"]
    assert planning["selected_plan"] is None
    assert eyes["OD"]["status"] == "ASSESSMENT INCOMPLETE"
    assert "Safety: ablation_um" in eyes["OD"]["missing"]
    assert len(planning["sequence"]) == 3
    for candidate in planning["sequence"]:
        assert candidate["status"] == "ASSESSMENT INCOMPLETE"
        assert candidate["ablation_um"] is None
        assert candidate["ablation_source"] == "ACTUAL_PLAN_MAX_ABLATION_REQUIRED"


def test_partial_zones_use_labeled_myopic_estimate_instead_of_unmatched_actual():
    _, eyes = _evaluate(od_plan=_plan(ablation_um=70.0, transition_zone_mm=8.5))
    planning = eyes["OD"]["planning"]
    assert planning["selected_plan"] == "Plan A"
    assert len(planning["sequence"]) == 1
    assert planning["sequence"][0]["ablation_um"] == 30.0
    assert planning["sequence"][0]["ablation_source"] == "CERAI_MYOPIC_ESTIMATE"


@pytest.mark.parametrize("zones, selected", [
    ({}, "Plan A"),
    ({"optical_zone_mm": 6.5, "transition_zone_mm": 9.0}, "Plan A"),
    ({"optical_zone_mm": 6.0, "transition_zone_mm": 8.5}, "Plan B"),
])
def test_existing_default_and_complete_zone_matches_keep_actual_ablation(zones, selected):
    _, eyes = _evaluate(od_plan=_plan(
        ablation_um=70.0,
        intended_entered_sphere_D=2.0,
        intended_cylinder_signed_D=0.0,
        **zones,
    ))
    planning = eyes["OD"]["planning"]
    assert planning["selected_plan"] == selected
    candidate = planning["sequence"][-1]
    assert candidate["plan"] == selected
    assert candidate["ablation_um"] == 70.0
    assert candidate["ablation_source"] == "ENTERED_OR_ACTUAL_PLAN_MAX_ABLATION"
    assert len(planning["sequence"]) == (1 if selected == "Plan A" else 2)
