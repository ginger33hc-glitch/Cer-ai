"""Protected upload boundary for keratoconus screening."""

import asyncio
import json
from math import isfinite
from uuid import uuid4

from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

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
        images: list[UploadFile] = File(...), refractions: str = Form(...)
    ):
        from operational_security import read_uploads
        from user_access import current_principal
        from .archive import archive_screening

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
        result = await core._run_image_assessment(
            payloads, None, plans, {}, {}, screening=True
        )
        usage_id = uuid4().hex
        result["archive"] = await asyncio.to_thread(
            archive_screening, core, result, payloads, principal, usage_id
        )
        consume = getattr(core, "_cerai_consume_demo_credit", None)
        if principal is not None and callable(consume):
            consume(principal.user_id, usage_id, "KERATOCONUS")
        return result

    core._cerai_keratoconus_module_installed = True
