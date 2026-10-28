"""Screening regressions: canonical thresholds, no surgical plan, protected transport."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from canonical_input_adapter import build_clinical_core_input
from clinical_core.keratoconus import evaluate_keratoconus
from canonical_runtime_service import _evaluate_keratoconus_case as evaluate_extracted
from keratoconus_module.web import validate_refractions


def fixture_case():
    eye = dict(
        Kmean_D=43.0,
        K2_D=44.0,
        central_pachy_um=550.0,
        pachy_thinnest_um=540.0,
        BAD_D=1.0,
        PPI_avg=1.0,
        F_Ele_Th_um=2.0,
        B_Ele_Th_um=5.0,
        I_S=0.2,
        srax_deg=10.0,
        posterior_Kmean_D=-6.0,
        topographic_astig_D=1.0,
    )
    extracted = {"eyes": [dict(eye, eye=e) for e in ("OD", "OS")]}
    refs = {
        e: dict(
            manifest_entered_sphere_D=-3.0,
            manifest_cylinder_signed_D=-1.0,
            manifest_axis_deg=90.0,
        )
        for e in ("OD", "OS")
    }
    return extracted, refs


def core_input():
    extracted, refs = fixture_case()
    return build_clinical_core_input(
        extracted["eyes"][0],
        refs["OD"],
        age_years=None,
        extracted=extracted,
        plan_already_resolved=True,
    )


@pytest.mark.parametrize(
    "value,label",
    [
        (1.6, "NEGATIVE"),
        (1.6001, "SUSPICIOUS"),
        (2.5999, "SUSPICIOUS"),
        (2.6, "POSITIVE"),
    ],
)
def test_existing_bad_boundaries(value, label):
    assert (
        evaluate_keratoconus(replace(core_input(), final_bad_d=value))[
            "screening_result"
        ]
        == label
    )


def test_surgical_fields_have_no_effect():
    inp = core_input()
    result = evaluate_keratoconus(inp)
    assert result["screening_result"] == "NEGATIVE"
    assert (
        evaluate_keratoconus(
            replace(
                inp,
                procedure="LASIK",
                flap_um=400.0,
                ablation_um=400.0,
                age_years=18,
                manifest_mrse_d=-20,
                intended_sphere_d=-20,
            )
        )
        == result
    )
    assert not {"erss", "procedural_safety", "procedure"}.intersection(result)


def test_one_ps3_moderate_is_suspicious_without_procedure():
    inp = core_input()
    inp = replace(inp, ps3_eye=replace(inp.ps3_eye, thinnest_um=495.0))
    assert evaluate_keratoconus(inp)["screening_result"] == "SUSPICIOUS"


def test_common_ps3_stop_is_positive():
    inp = core_input()
    inp = replace(inp, ps3_eye=replace(inp.ps3_eye, thinnest_um=460.0))
    assert evaluate_keratoconus(inp)["screening_result"] == "POSITIVE"


@pytest.mark.parametrize("i_s,label", [(1.0, "SUSPICIOUS"), (1.4, "POSITIVE")])
def test_existing_topography_boundaries(i_s, label):
    assert (
        evaluate_keratoconus(replace(core_input(), i_s_d=i_s))["screening_result"]
        == label
    )


def test_incomplete_not_positive_even_with_abnormal_bad():
    inp = core_input()
    assert (
        evaluate_keratoconus(replace(inp, final_bad_d=3.0, ps3_inter_eye=None))[
            "screening_result"
        ]
        == "NOT_ASSESSABLE"
    )


@pytest.mark.parametrize("key", ["critical_input_issues", "identity_warnings"])
def test_source_conflict_blocks_both_eyes(key):
    extracted, refs = fixture_case()
    extracted[key] = ["mismatched source"]
    assert {
        e["screening_result"] for e in evaluate_extracted(extracted, refs)["eyes"]
    } == {"NOT_ASSESSABLE"}


def test_no_mutation():
    extracted, refs = fixture_case()
    before = deepcopy((extracted, refs))
    evaluate_extracted(extracted, refs)
    assert (extracted, refs) == before


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {"OD": {}},
        {"OD": {"procedure": "PRK"}, "OS": {}},
        {
            e: dict(manifest_entered_sphere_D=True, manifest_cylinder_signed_D=0)
            for e in ("OD", "OS")
        },
        {
            e: dict(manifest_entered_sphere_D=0, manifest_cylinder_signed_D=-1)
            for e in ("OD", "OS")
        },
        {
            e: dict(
                manifest_entered_sphere_D=float("nan"), manifest_cylinder_signed_D=0
            )
            for e in ("OD", "OS")
        },
    ],
)
def test_reject_bad_refraction(bad):
    with pytest.raises(HTTPException):
        validate_refractions(bad)


def test_no_axis_needed_for_sphere_only():
    refs = {
        e: dict(manifest_entered_sphere_D=0, manifest_cylinder_signed_D=0)
        for e in ("OD", "OS")
    }
    assert validate_refractions(refs)["OD"]["manifest_axis_deg"] is None


def test_module_and_transport(monkeypatch):
    import canonical_engine
    import json

    core = canonical_engine.core
    extracted, refs = fixture_case()
    calls = []

    async def assess(payloads, age, plans, modifiers, metadata, *, screening=False):
        calls.append((screening, plans))
        return evaluate_extracted(extracted, plans)

    async def read(images):
        return [(b"synthetic", item.filename) for item in images]

    monkeypatch.setattr(core, "_run_image_assessment", assess)
    monkeypatch.setattr("operational_security.read_uploads", read)
    client = TestClient(canonical_engine.app)
    assert client.get("/keratoconus").status_code == 200
    assert "/keratoconus" in client.get("/clinical-modules").text
    response = client.post(
        "/keratoconus/analyze",
        data={"refractions": json.dumps(refs)},
        files=[("images", (f"{n}.png", b"synthetic", "image/png")) for n in range(5)],
    )
    assert response.status_code == 200, response.text
    assert response.json()["eyes"][0]["screening_result"] == "NEGATIVE"
    assert calls == [(True, refs)]
    assert (
        client.post(
            "/keratoconus/analyze",
            data={"refractions": json.dumps(refs)},
            files=[("images", ("one.png", b"a", "image/png"))],
        ).status_code
        == 422
    )


def test_protected_api():
    from operational_security import (
        _is_protected_path,
        _request_limit,
        MAX_REQUEST_BYTES,
    )

    assert _is_protected_path("/keratoconus/analyze")
    assert _request_limit("/keratoconus/analyze") == MAX_REQUEST_BYTES


def test_encrypted_archive_and_owner_redaction():
    from case_archive import EncryptedArchive, MemoryObjectStore, CaseArchiveRuntime
    from keratoconus_module.archive import archive_screening
    from historical_report import regenerate_bytes
    from archive_privacy import owner_assessment, MASKED
    import case_catalog

    extracted, refs = fixture_case()
    result = evaluate_extracted(extracted, refs)
    result["patient"]["name"] = "Synthetic Patient"
    result["source_contexts"] = [{"patient_name": "Synthetic Patient"}]
    result["issues"] = ["Identity conflict: Synthetic Patient"]
    actor = SimpleNamespace(
        user_id="test-doctor",
        username="test-doctor",
        display_name="Test Doctor",
        role="DOCTOR",
    )
    archive = EncryptedArchive(MemoryObjectStore(), b"a" * 32)
    core = SimpleNamespace(
        _cerai_case_archive_runtime=CaseArchiveRuntime(archive, required=True)
    )
    status = archive_screening(
        core,
        result,
        [(b"synthetic", "source.png")],
        actor,
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    assert status["status"] == "ARCHIVED"
    snapshot = archive.load_assessment(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", status["revision_id"]
    )
    assert snapshot["module"] == "KERATOCONUS"
    assert archive.get_bytes(
        archive.find_report(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", status["revision_id"], "tr", "pdf"
        )
    ).startswith(b"%PDF")
    assert owner_assessment(snapshot)["patient"]["name"] == MASKED
    assert "Synthetic Patient" not in str(owner_assessment(snapshot))
    assert (
        case_catalog.get_entry(
            archive, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", status["revision_id"]
        )["module"]
        == "KERATOCONUS"
    )
    assert regenerate_bytes(
        archive,
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        status["revision_id"],
        kind="pdf",
        locale="tr",
        pdf_builder=None,
        docx_builder=None,
        owner_deidentified=True,
    ).startswith(b"%PDF")


def test_screening_uses_shared_extraction_without_requiring_intended_or_procedure(
    monkeypatch,
):
    import asyncio
    import app
    import assessment_workflow
    from contextlib import asynccontextmanager
    from test_mandatory_source_set_policy import complete_set

    sources = complete_set(False)
    payloads = [(b"image", f"source-{i}.png") for i in range(5)]
    by_name = {name: source for source, (_, name) in zip(sources, payloads)}
    extracted, refs = fixture_case()

    @asynccontextmanager
    async def slot():
        yield

    monkeypatch.setattr("operational_security.analysis_slot", slot)
    monkeypatch.setattr("operational_security.admit_analysis", lambda: None)
    monkeypatch.setattr(
        app, "extract_one_image", lambda raw, name, authority: by_name[name]
    )
    monkeypatch.setattr(
        app.pentacam_targeted_reread,
        "enrich_extraction",
        lambda core, result, *args, **kw: result,
    )
    monkeypatch.setattr(
        app.pentacam_targeted_reread,
        "verify_threshold_level_readings",
        lambda core, result, *args, **kw: result,
    )
    monkeypatch.setattr(
        app.geometric_srax_policy, "enrich_extraction", lambda result, *args: result
    )
    monkeypatch.setattr(
        app, "merge_extractions", lambda results, authority: deepcopy(extracted)
    )
    monkeypatch.setattr(
        assessment_workflow,
        "begin",
        lambda *a, **k: pytest.fail("Surgical workflow must not run"),
    )
    response = asyncio.run(
        app._run_image_assessment(payloads, None, refs, {}, {}, screening=True)
    )
    assert [eye["screening_result"] for eye in response["eyes"]] == [
        "NEGATIVE",
        "NEGATIVE",
    ]


def test_named_user_boundary_covers_screening():
    from test_named_user_ui import make_client

    client, _ = make_client()
    assert client.get("/keratoconus").status_code == 303
    response = client.post("/keratoconus/analyze")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_single_canonical_case_entry():
    from canonical_runtime_service import evaluate_case

    extracted, refs = fixture_case()
    response = evaluate_case(
        extracted,
        None,
        refs,
        {},
        assessment_mode="KERATOCONUS",
        software_version="test-version",
    )
    assert response["versions"]["software"] == "test-version"
    assert response["module"] == "KERATOCONUS"
    with pytest.raises(ValueError):
        evaluate_case(extracted, None, refs, {}, assessment_mode="unknown")
