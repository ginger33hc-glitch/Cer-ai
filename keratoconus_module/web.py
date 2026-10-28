"""Protected upload boundary for keratoconus screening."""

import asyncio
from contextlib import suppress
import json
from math import isfinite

from fastapi import Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from assessment_progress import bind_progress_sink, publish_progress

from clinical_core.refraction import normalize_minus_cylinder


def validate_refractions(value):
    if not isinstance(value, dict) or set(value) != {"OD", "OS"}:
        raise HTTPException(422, "Enter refraction for both OD and OS.")
    result = {}
    allowed = {
        "manifest_entered_sphere_D",
        "manifest_cylinder_signed_D",
        "manifest_axis_deg",
    }
    for eye_id, refraction in value.items():
        if not isinstance(refraction, dict) or set(refraction) - allowed:
            raise HTTPException(
                422, "Only manifest sphere, cylinder and axis are accepted."
            )
        sphere = refraction.get("manifest_entered_sphere_D")
        cylinder = refraction.get("manifest_cylinder_signed_D")
        axis = refraction.get("manifest_axis_deg")
        finite = lambda v: (
            isinstance(v, (float, int)) and not isinstance(v, bool) and isfinite(v)
        )
        if (
            not finite(sphere)
            or not finite(cylinder)
            or (axis is not None and not finite(axis))
        ):
            raise HTTPException(
                422, f"{eye_id}: enter finite sphere, cylinder and axis values."
            )
        if axis is not None and not 0 <= axis <= 180:
            raise HTTPException(
                422, f"{eye_id}: axis must be between 0 and 180 degrees."
            )
        if cylinder != 0 and axis is None:
            raise HTTPException(422, f"{eye_id}: cylinder axis is required.")
        if normalize_minus_cylinder(sphere, cylinder, axis) is None:
            raise HTTPException(422, f"{eye_id}: invalid refraction.")
        result[eye_id] = {
            "manifest_entered_sphere_D": sphere,
            "manifest_cylinder_signed_D": cylinder,
            "manifest_axis_deg": axis,
        }
    return result


def install(core):
    if getattr(core, "_cerai_keratoconus_module_installed", False):
        return

    @core.app.get("/keratoconus", include_in_schema=False)
    def screening_page():
        return FileResponse(
            "static/keratoconus.html",
            media_type="text/html",
            headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex,nofollow"},
        )

    @core.app.post("/keratoconus/analyze")
    async def screening_analyze(
        images: list[UploadFile] = File(...),
        refractions: str = Form(...),
        patient_name: str = Form(..., min_length=1, max_length=200),
        patient_age: int = Form(..., ge=1, le=120),
    ):
        return await run_screening(core, images, refractions, patient_name, patient_age)

    @core.app.post("/keratoconus/stream")
    async def screening_stream(
        images: list[UploadFile] = File(...),
        refractions: str = Form(...),
        patient_name: str = Form(..., min_length=1, max_length=200),
        patient_age: int = Form(..., ge=1, le=120),
    ):
        return StreamingResponse(
            screening_events(core, images, refractions, patient_name, patient_age),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @core.app.post("/keratoconus/complete")
    async def screening_complete(payload: dict = Body(...)):
        import assessment_workflow

        with assessment_workflow._lock:
            session = assessment_workflow._session(payload.get("assessment_token"))
            if session.get("assessment_mode") != "KERATOCONUS":
                raise HTTPException(409, "Use the correct assessment module.")
        response = await asyncio.to_thread(assessment_workflow.complete, core, payload)
        return screening_payload(response)

    core._cerai_keratoconus_module_installed = True


async def run_screening(core, images, refractions, patient_name, patient_age):
    from operational_security import read_uploads
    from user_access import current_principal

    patient_name = " ".join(patient_name.split())
    if not patient_name:
        raise HTTPException(422, "Enter the patient name.")
    try:
        plans = validate_refractions(json.loads(refractions))
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "Invalid refraction JSON.") from exc
    if len(images) != 5:
        raise HTTPException(
            422,
            "Upload exactly 5 Pentacam images: OD/OS Four Maps Refractive, OD/OS BAD Display, and Show 2 Exams Topometric.",
        )
    principal = current_principal()
    assert_credit = getattr(core, "_cerai_assert_demo_credit", None)
    if principal is not None and callable(assert_credit):
        assert_credit(principal.user_id)
    payloads = await read_uploads(images)
    await publish_progress("UPLOAD_COMPLETE")
    result = await core._run_image_assessment(
        payloads, patient_age, plans, {}, {"name": patient_name}, screening=True
    )
    return screening_payload(result)


def screening_payload(response):
    """Preserve the shared workflow contract and the existing ready-screen shape."""
    if response.get("workflow_status") == "READY":
        return {
            **response["decision"],
            "workflow_status": "READY",
            "assessment_token": response["assessment_token"],
        }
    return response


def progress_event(code, details):
    """Operational milestone percentage, not elapsed-time or clinical confidence."""
    percent = {
        "UPLOAD_COMPLETE": 10,
        "VERIFYING_REQUIRED_VALUES": 70,
        "CALCULATING_ASSESSMENT": 85,
        "ARCHIVING": 95,
    }.get(code, 0)
    if code == "ANALYZING_IMAGES":
        total = max(1, int(details.get("total_images", 5)))
        completed = min(total, max(0, int(details.get("completed_images", 0))))
        percent = 10 + round(50 * completed / total)
    return {
        "type": "progress",
        "code": code,
        "percent": percent,
        **{k: details[k] for k in ("completed_images", "total_images") if k in details},
    }


async def screening_events(core, images, refractions, patient_name, patient_age):
    """Stream the existing canonical assessment's published milestones only."""
    queue = asyncio.Queue(maxsize=32)

    async def receive(code, details):
        await queue.put(progress_event(code, details))

    async def process():
        try:
            with bind_progress_sink(receive):
                result = await run_screening(
                    core, images, refractions, patient_name, patient_age
                )
            await queue.put(
                {
                    "type": "result",
                    "percent": 85
                    if result.get("workflow_status") == "NEEDS_INPUT"
                    else 100,
                    "result": result,
                }
            )
        except HTTPException as exc:
            await queue.put(
                {"type": "error", "status": exc.status_code, "detail": exc.detail}
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            await queue.put(
                {
                    "type": "error",
                    "status": 500,
                    "detail": "Screening could not be completed. Please retry.",
                }
            )

    task = asyncio.create_task(process())
    try:
        while True:
            event = await queue.get()
            yield json.dumps(event, ensure_ascii=False) + "\n"
            if event["type"] in {"result", "error"}:
                break
    finally:
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError):
            await task
