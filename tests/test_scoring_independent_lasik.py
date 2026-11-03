"""Synthetic regressions: calculations continue; scoring STOP is never cleared."""
from types import SimpleNamespace

import pytest

import assessment_workflow as workflow
from canonical_runtime_service import evaluate_case
from test_step11_analyze_completion_workflow import _eye, _plan, _modifiers


@pytest.mark.parametrize("changes,section", [
    ({"I_S": 1.5}, "randleman"),
    ({"BAD_D": 2.6}, "bad"),
    ({"PPI_avg": 1.3}, "ps3"),
    ({"K2_D": 47.2, "central_pachy_um": 510, "B_Ele_Th_um": 18}, "nice"),
    ({"BAD_D": 2.6, "PPI_avg": 1.3, "I_S": 1.5}, "bad"),
])
def test_scoring_stop_keeps_lasik_calculations_and_untouched_other_eye(changes, section):
    result = evaluate_case({"eyes": [_eye("OD", **changes), _eye("OS")]}, 35,
                          {"OD": _plan(), "OS": _plan()}, _modifiers())
    od, os = result["eyes"]
    report = od["report_payload"]
    assert report[section]["status"] == "STOP-DEFER"
    assert od["status"] == result["status"] == "STOP-DEFER"
    assert report["procedure"] == "LASIK"
    assert report["tissue_safety"]["LASIK_RSB_um"] == 395
    assert report["tissue_safety"]["LASIK_PTA_percent"] == pytest.approx(150 / 545 * 100)
    assert report["tissue_safety"]["status"] == "PASS"
    assert report["planning"]["selected_plan"] == "Plan A"
    assert report["microkeratome_planning"]["vacuum_ring_mm"] is not None
    assert report["microkeratome_planning"]["assessment_gate"] == "STOP-DEFER"
    assert report["microkeratome_planning"]["warnings"]
    assert result["procedure_transitions"] == []
    assert os["status"] == "PASS"


def test_reported_40_micron_case_is_ready_without_unnecessary_fallback_depth():
    plan = _plan(ablation_um=40., optical_zone_mm=6.5, transition_zone_mm=9.,
                 manifest_entered_sphere_D=.75, manifest_cylinder_signed_D=1.75,
                 intended_entered_sphere_D=.75, intended_cylinder_signed_D=1.75)
    session = {"extracted": {"eyes": [_eye("OD"), _eye("OS", pachy_thinnest_um=500)]},
               "ready": None, "source_images": []}
    result = workflow._respond(SimpleNamespace(APP_VERSION="synthetic"), "token", session, 21,
                               {"OD": _plan(), "OS": plan}, _modifiers(), {"name": "Synthetic"}, {})
    assert result["workflow_status"] == "READY"
    assert result["input_requests"] == []
    assert result["effective_eye_plans"]["OS"]["ablation_um"] == 40
    assert result["effective_eye_plans"]["OS"]["procedure"] == "LASIK"
    os = result["decision"]["eyes"][1]["report_payload"]
    assert os["randleman"]["status"] == "STOP-DEFER"
    assert os["tissue_safety"]["status"] == "PASS"
    assert os["microkeratome_planning"]["vacuum_ring_mm"] is not None


def test_tissue_failure_preserves_original_lasik_ml7_and_rechecks_prk():
    plan = _plan(ablation_um=166, lasik_bc_ablation_um=166, optical_zone_mm=6.5, transition_zone_mm=9.)
    result = evaluate_case({"eyes": [_eye("OD", pachy_thinnest_um=600, BAD_D=2.6), _eye("OS")]}, 35,
                          {"OD": plan, "OS": _plan()}, _modifiers())
    od = result["eyes"][0]
    original = od["lasik_assessment"]["report_payload"]
    assert len(original["planning"]["sequence"]) == 3
    assert all(row["procedural_safety"]["hard_stops"]["lasik_pta"] for row in original["planning"]["sequence"])
    assert original["microkeratome_planning"]["vacuum_ring_mm"] == 9
    assert original["planning"]["selected_procedure_plan"]["flap_um"] == 90
    assert original["tissue_safety"]["LASIK_RSB_um"] == 344
    assert od["report_payload"]["procedure"] == "PRK"
    assert od["report_payload"]["tissue_safety"]["PRK_RST_um"] == 384
    assert od["report_payload"]["tissue_safety"]["PRK_PTA_percent"] == 36
    assert od["report_payload"]["bad"]["status"] == od["status"] == "STOP-DEFER"
    assert od["report_payload"]["prior_lasik_assessment"] == original
    assert len(result["procedure_transitions"]) == 1


def test_missing_fallback_depth_is_not_a_failed_tissue_test():
    plan = _plan(ablation_um=200, optical_zone_mm=6.5, transition_zone_mm=9.,
                 intended_entered_sphere_D=2., intended_cylinder_signed_D=0.)
    result = evaluate_case({"eyes": [_eye("OD", BAD_D=2.6), _eye("OS")]}, 35,
                          {"OD": plan, "OS": _plan()}, _modifiers())
    assert result["procedure_transitions"] == []
    assert result["effective_eye_plans"]["OD"]["procedure"] == "LASIK"
    assert "Safety: ablation_um" in result["eyes"][0]["missing"]


def test_scoring_stop_requests_missing_verified_ml7_source_instead_of_guessing():
    session = {"extracted": {"eyes": [_eye("OD", BAD_D=2.6, corneal_diameter_mm=None), _eye("OS")]},
               "ready": None, "source_images": []}
    result = workflow._respond(SimpleNamespace(APP_VERSION="synthetic"), "token", session, 35,
                               {"OD": _plan(), "OS": _plan()}, _modifiers(), {"name": "Synthetic"}, {})
    assert result["workflow_status"] == "NEEDS_INPUT"
    assert any(item["eye"] == "OD" and item["key"] == "corneal_diameter_mm" for item in result["input_requests"])
    assert result["hard_stop_summary"]["status"] == "STOP-DEFER"
