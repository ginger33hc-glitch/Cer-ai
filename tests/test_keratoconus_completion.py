"""KC uses the same session, completion/provenance and canonical runtime as refraction."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import assessment_workflow as workflow
import canonical_engine
from test_keratoconus import fixture_case as original_fixture_case
from keratoconus_module.web import screening_payload


def fixture_case():
    extracted, refs = original_fixture_case()
    for eye in extracted["eyes"]:
        fields = [key for key, value in eye.items() if isinstance(value, (int, float))]
        eye["table_verified_numeric_fields"] = fields
        eye["field_provenance"] = {
            key: [{"source": "SYNTHETIC_CANONICAL_TABLE"}] for key in fields
        }
    return extracted, refs


@pytest.fixture(autouse=True)
def cleanup():
    workflow._sessions.clear()
    yield
    workflow._sessions.clear()


def begin(extracted, refs):
    return workflow.begin(
        canonical_engine.core,
        extracted,
        17,
        refs,
        {},
        {"name": "SURGEON NAME"},
        assessment_mode="KERATOCONUS",
    )


def test_unreadable_values_request_surgeon_and_resume_without_images():
    original, refs = fixture_case()
    extracted = deepcopy(original)
    for eye in extracted["eyes"]:
        for key in ("BAD_D", "K2_D", "I_S", "PPI_avg", "Kmean_D", "posterior_Kmean_D"):
            eye[key] = None
    response = begin(extracted, refs)
    assert response["workflow_status"] == "NEEDS_INPUT"
    assert response["report_token"] is None
    assert response["patient_metadata"]["name"] == "SURGEON NAME"
    assert response["patient_metadata"]["age"] == 17
    assert response["input_requests"]
    keys = {r["key"] for r in response["input_requests"]}
    assert {"BAD_D", "K2_D", "I_S", "PPI_avg", "Kmean_D", "posterior_Kmean_D"} <= keys
    assert not keys.intersection(
        {"age", "patient_name", "procedure", "prior", "flap_um", "ablation_um", "RSB"}
    )
    for _ in range(4):
        if response["workflow_status"] == "READY":
            break
        values = {}
        for request in response["input_requests"]:
            assert request["destination"] == "measurement", request
            assert request["kind"] == "number", request
            source = next(e for e in original["eyes"] if e["eye"] == request["eye"])
            values.setdefault(request["eye"], {})[request["key"]] = source[
                request["key"]
            ]
        response = workflow.complete(
            canonical_engine.core,
            {
                "assessment_token": response["assessment_token"],
                "clinical_overrides": values,
                "age": 99,
                "patient_metadata": {"name": "FORGED"},
                "eye_plans": {"OD": {"procedure": "LASIK"}},
            },
        )
    assert response["workflow_status"] == "READY"
    result = screening_payload(response)
    assert (
        result["patient"]["name"] == "SURGEON NAME" and result["patient"]["age"] == 17
    )
    assert {e["screening_result"] for e in result["eyes"]} == {"NEGATIVE"}
    eye = workflow._session(response["assessment_token"])["extracted"]["eyes"][0]
    assert eye["field_provenance"]["BAD_D"] == [{"source": "SURGEON_CONFIRMED"}]
    assert "BAD_D" in eye["surgeon_verified_numeric_fields"]


def test_srax_and_ps3_exception_follow_existing_sequential_completion():
    extracted, refs = fixture_case()
    extracted["eyes"][0].update(srax_deg=25, topographic_astig_D=0.5)
    response = begin(extracted, refs)
    assert any(r["key"] == "srax" for r in response["input_requests"])
    response = workflow.complete(
        canonical_engine.core,
        {
            "assessment_token": response["assessment_token"],
            "clinical_overrides": {"OD": {"srax": "YES"}},
        },
    )
    assert response["workflow_status"] == "NEEDS_INPUT"
    assert any(r["key"] == "ps3_srax_exception" for r in response["input_requests"])
    response = workflow.complete(
        canonical_engine.core,
        {
            "assessment_token": response["assessment_token"],
            "clinical_overrides": {"OD": {"ps3_srax_exception": "NO"}},
        },
    )
    assert response["workflow_status"] == "READY"
    assert response["decision"]["eyes"][0]["screening_result"] == "POSITIVE"


def test_unrequested_values_are_rejected():
    extracted, refs = fixture_case()
    extracted["eyes"][0]["BAD_D"] = None
    response = begin(extracted, refs)
    with pytest.raises(HTTPException) as error:
        workflow.complete(
            canonical_engine.core,
            {
                "assessment_token": response["assessment_token"],
                "clinical_overrides": {"OD": {"K2_D": 33}},
            },
        )
    assert error.value.status_code == 409


def test_screening_session_cannot_be_accessed_by_another_user():
    from user_access import bind_current_principal, reset_current_principal

    extracted, refs = fixture_case()
    extracted["eyes"][0]["BAD_D"] = None
    token = bind_current_principal(
        SimpleNamespace(user_id="A", display_name="Doctor A")
    )
    try:
        response = begin(extracted, refs)
    finally:
        reset_current_principal(token)
    token = bind_current_principal(
        SimpleNamespace(user_id="B", display_name="Doctor B")
    )
    try:
        with pytest.raises(HTTPException) as error:
            workflow._session(response["assessment_token"])
        assert error.value.status_code == 403
    finally:
        reset_current_principal(token)


def test_surgeon_identity_is_not_reread_or_replaced_during_enrichment(monkeypatch):
    import asyncio
    import app
    from contextlib import asynccontextmanager
    from test_mandatory_source_set_policy import complete_set

    sources = complete_set(False)
    for source in sources:
        source["document_context"].update(
            patient_name="WRONG DOCUMENT NAME",
            patient_first_name="WRONG",
            patient_last_name="NAME",
            patient_age_years=88,
            patient_date_of_birth="1938-01-01",
            missing_or_unreadable=[
                "patient_name",
                "patient_age_years",
                "patient_date_of_birth",
            ],
        )
    payloads = [(b"image", f"{i}.png") for i in range(5)]
    by_name = {name: source for source, (_, name) in zip(sources, payloads)}

    @asynccontextmanager
    async def slot():
        yield

    monkeypatch.setattr("operational_security.admit_analysis", lambda: None)
    monkeypatch.setattr("operational_security.analysis_slot", slot)

    def extract(raw, name, authority):
        assert authority["patient"] == {"name", "age"}
        prompt = app.surgeon_authority_prompt(authority)
        assert "Do not inspect or transcribe any image name" in prompt
        assert "Do not inspect or transcribe image age" in prompt
        return deepcopy(by_name[name])

    def enrich(core, result, *args, **kwargs):
        assert kwargs["seek_patient_age"] is False
        return result

    monkeypatch.setattr(app, "extract_one_image", extract)
    monkeypatch.setattr(app.pentacam_targeted_reread, "enrich_extraction", enrich)
    monkeypatch.setattr(
        app.pentacam_targeted_reread,
        "verify_threshold_level_readings",
        lambda core, result, *a, **k: result,
    )
    monkeypatch.setattr(
        app.geometric_srax_policy, "enrich_extraction", lambda result, *a: result
    )
    extracted, refs = fixture_case()

    def merge(results, authority):
        for source in results:
            ctx = source["document_context"]
            assert (
                ctx["patient_name"] is None
                and ctx["patient_age_years"] is None
                and ctx["patient_date_of_birth"] is None
            )
            assert not set(ctx["missing_or_unreadable"]).intersection(
                {"patient_name", "patient_age_years", "patient_date_of_birth"}
            )
        return extracted

    monkeypatch.setattr(app, "merge_extractions", merge)
    response = asyncio.run(
        app._run_image_assessment(
            payloads, 17, refs, {}, {"name": "SURGEON NAME"}, screening=True
        )
    )
    assert response["workflow_status"] == "READY"
    assert response["decision"]["patient"]["name"] == "SURGEON NAME"
    assert response["decision"]["patient"]["age"] == 17


def test_completion_keeps_source_archive_and_charges_once():
    from case_archive import EncryptedArchive, MemoryObjectStore, CaseArchiveRuntime
    from user_access import Principal, bind_current_principal, reset_current_principal
    from types import SimpleNamespace

    archive = EncryptedArchive(MemoryObjectStore(), b"x" * 32)
    credits = []
    actor = Principal("doctor-a", "doctor", "Doctor A", "DOCTOR")
    core = SimpleNamespace(
        APP_VERSION="test",
        _cerai_case_archive_runtime=CaseArchiveRuntime(archive, required=True),
        _cerai_consume_demo_credit=lambda *args: credits.append(args),
    )
    extracted, refs = fixture_case()
    extracted["eyes"][0]["BAD_D"] = None
    payloads = [(b"synthetic", f"{i}.png") for i in range(5)]
    bound = bind_current_principal(actor)
    try:
        response = workflow.begin(
            core,
            extracted,
            17,
            refs,
            {},
            {"name": "SURGEON NAME"},
            source_images=payloads,
            assessment_mode="KERATOCONUS",
        )
        assert response["workflow_status"] == "NEEDS_INPUT"
        case_id = response["archive"]["case_id"]
        assert len(archive.list_sources(case_id)) == 5
        payload = {
            "assessment_token": response["assessment_token"],
            "clinical_overrides": {"OD": {"BAD_D": 1}},
        }
        response = workflow.complete(core, payload)
        assert response["workflow_status"] == "READY"
        assert response["decision"]["archive"]["case_id"] == case_id
        revision = response["decision"]["archive"]["revision_id"]
        snapshot = archive.load_assessment(case_id, revision)
        assert (
            snapshot["patient"]["name"] == "SURGEON NAME"
            and snapshot["patient"]["age"] == 17
        )
        assert snapshot["eyes"][0]["source_provenance"]["field_provenance"][
            "BAD_D"
        ] == [{"source": "SURGEON_CONFIRMED"}]
        again = workflow.complete(core, payload)
        assert again["decision"]["archive"]["revision_id"] == revision
        assert len(credits) == 1
    finally:
        reset_current_principal(bound)


def test_one_eye_source_conflict_does_not_request_other_eye_override():
    from extraction_guard import apply_extraction_validation

    extracted, refs = fixture_case()
    extracted["eyes"][0]["data_conflicts"] = ["BAD_D: 1 versus 3"]
    extracted = apply_extraction_validation(extracted)
    response = begin(extracted, refs)
    requests = {(r["eye"], r["key"]) for r in response["input_requests"]}
    assert requests == {("OD", "BAD_D")}
    response = workflow.complete(
        canonical_engine.core,
        {
            "assessment_token": response["assessment_token"],
            "clinical_overrides": {"OD": {"BAD_D": 1}},
        },
    )
    assert response["workflow_status"] == "READY"
