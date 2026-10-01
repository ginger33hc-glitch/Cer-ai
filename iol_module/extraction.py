"""Source-locked transcription for IOLMaster 500 and Pentacam reports."""

from __future__ import annotations

import json
import logging
from io import BytesIO

from PIL import Image, ImageOps
from pydantic import TypeAdapter, ValidationError

from .models import PosteriorCorneaInput, complete_posterior_axes
import unicodedata
from typing import Any

EYE_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["axial_length_mm", "axial_length_edited_marker", "k1_d", "k1_axis_deg", "k2_d", "k2_axis_deg", "acd_mm", "lens_thickness_mm"],
    "properties": {
        "axial_length_mm": {"type": ["number", "null"]},
        "axial_length_edited_marker": {"type": "boolean"},
        "k1_d": {"type": ["number", "null"]}, "k1_axis_deg": {"type": ["number", "null"]},
        "k2_d": {"type": ["number", "null"]}, "k2_axis_deg": {"type": ["number", "null"]},
        "acd_mm": {"type": ["number", "null"]},
        "lens_thickness_mm": {"type": ["number", "null"]},
    },
}

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["document_type", "eye", "patient_name", "patient_age_years", "pentacam", "cornea_back", "iolmaster500", "unreadable_fields"],
    "properties": {
        "document_type": {"type": "string", "enum": ["PENTACAM_CATARACT_PREOP", "PENTACAM_4_MAPS_REFRACTIVE", "IOLMASTER_500_BIOMETRY", "OTHER"]},
        "eye": {"type": "string", "enum": ["OD", "OS", "BOTH", "UNKNOWN"]},
        "patient_name": {"type": ["string", "null"]},
        "patient_age_years": {"type": ["integer", "null"]},
        "pentacam": {
            "type": "object", "additionalProperties": False,
            "required": ["total_corneal_hoa_4mm_um", "angle_kappa_mm", "angle_alpha_mm", "pupil_dia_3d_mm", "cct_pachy_vertex_um", "hwtw_mm", "acd_internal_mm"],
            "properties": {
                "total_corneal_hoa_4mm_um": {"type": ["number", "null"]},
                "angle_kappa_mm": {"type": ["number", "null"]},
                "angle_alpha_mm": {"type": ["number", "null"]},
                "pupil_dia_3d_mm": {"type": ["number", "null"]},
                "cct_pachy_vertex_um": {"type": ["number", "null"]},
                "hwtw_mm": {"type": ["number", "null"]},
                "acd_internal_mm": {"type": ["number", "null"]},
            },
        },
        "cornea_back": {
            "type": "object", "additionalProperties": False,
            "required": ["k1_d", "k2_d", "k1_axis_deg", "k2_axis_deg"],
            "properties": {
                "k1_d": {"type": ["number", "null"]},
                "k2_d": {"type": ["number", "null"]},
                "k1_axis_deg": {"type": ["number", "null"]},
                "k2_axis_deg": {"type": ["number", "null"]},
            },
        },
        "iolmaster500": {
            "type": "object", "additionalProperties": False,
            "required": ["device_version", "printed_formula", "printed_target_refraction_d", "OD", "OS"],
            "properties": {
                "device_version": {"type": ["string", "null"]},
                "printed_formula": {"type": ["string", "null"]},
                "printed_target_refraction_d": {"type": ["number", "null"]},
                "OD": EYE_SCHEMA, "OS": EYE_SCHEMA,
            },
        },
        "unreadable_fields": {"type": "array", "items": {"type": "string"}},
    },
}

PROMPT = """
You are transcribing one ophthalmic source image for the independent CER-AI IOL module.
Return only explicitly printed, readable values. Never estimate, calculate, average, copy
from the fellow eye, or substitute a similar field. Nonmatching document objects use nulls.

Classify as PENTACAM_CATARACT_PREOP, PENTACAM_4_MAPS_REFRACTIVE,
IOLMASTER_500_BIOMETRY, or OTHER. Preserve
OD/right or OS/left; use BOTH for a bilateral IOLMaster page.

Pentacam Cataract Pre-Op source locks:
- Total Corneal HOA (4mm), Chord µ (approved kappa mapping), Chord α, Pupil Dia (3D).
- cct_pachy_vertex_um is Pachy Vertex, never Thinnest.
- hwtw_mm is HWTW.
- acd_internal_mm is ACD (Int.), the true internal ACD excluding corneal thickness.
  Never substitute ACD (Ext.).
TCRP, SimK and Diff. are not authoritative and must not be extracted.

Pentacam 4 Maps Refractive: transcribe the left-middle numeric panel's "Cornea Back"
K1, K2 (preserve printed negative signs), and their explicitly printed axes.
Map an explicitly labeled posterior "Axis (steep)" to k2_axis_deg and
"Axis (flat)" to k1_axis_deg. If the panel prints only the steep axis,
return that axis and null for the unprinted flat axis; code handles orthogonality.
An unlabeled/ambiguous Axis stays null. Do not use Cornea Front, color maps,
Rh/Rv or Rf/Rs radii, or infer missing axes. These measurements belong only
to the indicated eye.

IOLMaster 500 source locks: use only the upper biometry block, never lower IOL tables.
Transcribe AL, K1 and axis, K2 and axis, and ACD separately for OD and OS. Set the AL
edited marker only when an asterisk is printed. Transcribe lens thickness only if explicitly
printed. Preserve device version, printed formula and target when readable. IOLMaster K1/K2
and axes are the sole source for the toric trigger.

For unreadable recognized-document fields return null and add the fully qualified key to
unreadable_fields.
"""


def validate_source_bundle(
    sources: list[dict[str, Any]],
    *,
    surgeon_patient_name: str | None = None,
) -> dict[str, Any]:
    """Fail closed before values from different IOL reports can be combined."""
    expected = {
        "PENTACAM_CATARACT_PREOP", "PENTACAM_4_MAPS_REFRACTIVE",
        "IOLMASTER_500_BIOMETRY",
    }
    documents = [item.get("extraction") or {} for item in sources]
    types = [item.get("document_type") for item in documents]
    bilateral = len(documents) == 5
    count = 2 if bilateral else 1
    if (len(documents) not in {3, 5} or set(types) != expected
            or types.count("IOLMASTER_500_BIOMETRY") != 1
            or types.count("PENTACAM_CATARACT_PREOP") != count
            or types.count("PENTACAM_4_MAPS_REFRACTIVE") != count):
        raise ValueError("Upload 3 images for one eye or 5 for both eyes: Cataract Pre-Op and 4 Maps Refractive for each eye, plus one shared IOLMaster 500 report.")

    authoritative_name = " ".join(str(surgeon_patient_name or "").split())
    names = [" ".join(str(item.get("patient_name") or "").split()) for item in documents]
    source_name_review_required = False
    if not authoritative_name:
        if any(not name for name in names):
            raise ValueError("Patient name must be readable on all source reports before combining their measurements.")
        normalized = {unicodedata.normalize("NFKC", name).casefold() for name in names}
        if len(normalized) != 1:
            raise ValueError("Patient names differ across the source reports. Check the source images.")
        authoritative_name = names[types.index("PENTACAM_CATARACT_PREOP")]
    else:
        authoritative_normalized = unicodedata.normalize(
            "NFKC", authoritative_name
        ).casefold()
        source_name_review_required = any(
            not name
            or unicodedata.normalize("NFKC", name).casefold()
            != authoritative_normalized
            for name in names
        )

    preops = [item for item in documents if item.get("document_type") == "PENTACAM_CATARACT_PREOP"]
    maps = [item for item in documents if item.get("document_type") == "PENTACAM_4_MAPS_REFRACTIVE"]
    eyes = [item.get("eye") for item in preops]
    if any(eye not in {"OD", "OS"} for eye in eyes):
        raise ValueError("The operative eye must be readable on the Pentacam Cataract Pre-Op report.")
    if len(set(eyes)) != count:
        raise ValueError("Both-eye assessment requires separate OD and OS Pentacam reports; duplicate eyes are not accepted.")
    if sorted((item.get("eye") or "UNKNOWN") for item in maps) != sorted(eyes):
        raise ValueError("The 4 Maps Refractive report must show the same operative eye.")
    iolmaster = documents[types.index("IOLMASTER_500_BIOMETRY")]
    if (iolmaster.get("eye") not in ({"BOTH"} if bilateral else {"BOTH", eyes[0]})
            or any(not isinstance((iolmaster.get("iolmaster500") or {}).get(eye), dict) for eye in eyes)):
        raise ValueError("The IOLMaster report must include biometry for the operative eye.")
    identity: dict[str, Any] = {"patient_name": authoritative_name, "eye": "BOTH" if bilateral else eyes[0]}
    if bilateral:
        identity["eyes"] = ["OD", "OS"]
    if source_name_review_required:
        identity["source_name_review_required"] = True
    return identity


def extract_image(core: Any, raw: bytes, filename: str) -> dict[str, Any]:
    response = core.openai_client().responses.create(
        model=core.MODEL, store=False, reasoning={"effort": "low"},
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": PROMPT},
            {"type": "input_image", "image_url": core.data_url(raw, filename), "detail": "original"},
        ]}],
        text={"verbosity": "low", "format": {"type": "json_schema", "name": "cerai_iol_source_extraction", "strict": True, "schema": EXTRACTION_SCHEMA}},
    )
    if not response.output_text or not response.output_text.strip():
        raise RuntimeError("IOL source extraction returned empty output")
    result = json.loads(response.output_text)
    result = reread_cornea_back(core, raw, filename, result)
    if result.get("document_type") == "PENTACAM_4_MAPS_REFRACTIVE" and result.get("eye") in {"OD", "OS"}:
        back = result.get("cornea_back") or {}
        completed = complete_posterior_axes(back)
        derived = [key for key in completed if back.get(key) is None and completed[key] is not None]
        result["cornea_back"] = completed
        result["cornea_back_derived_fields"] = derived
        result["unreadable_fields"] = [key for key in result.get("unreadable_fields", [])
                                       if key not in {"cornea_back." + field for field in derived}]
    return result


logger = logging.getLogger(__name__)


def reread_cornea_back(core: Any, raw: bytes, filename: str, result: dict[str, Any]) -> dict[str, Any]:
    """Retry missing posterior measurements once, on the same source only."""
    if result.get("document_type") != "PENTACAM_4_MAPS_REFRACTIVE" or result.get("eye") not in {"OD", "OS"}:
        return result
    fields = EXTRACTION_SCHEMA["properties"]["cornea_back"]["required"]
    back = result.get("cornea_back") or {}
    completed = complete_posterior_axes(back)
    missing = [key for key in fields if completed.get(key) is None]
    if not missing:
        return result
    logger.info("IOL_CORNEA_BACK_REREAD start eye=%s missing=%s", result["eye"], ",".join(missing))
    try:
        # Keep the entire vertical panel: different report layouts move its rows.
        # Full source is also supplied for header laterality and panel context.
        with Image.open(BytesIO(raw)) as opened:
            if opened.width * opened.height > 40_000_000:
                raise ValueError("source exceeds reread pixel limit")
            image = ImageOps.exif_transpose(opened).convert("RGB")
            crop = image.crop((0, 0, max(1, round(image.width * 0.60)), image.height))
            output = BytesIO()
            crop.save(output, format="PNG")
        schema = {
            "type": "object", "additionalProperties": False,
            "required": ["document_type", "eye", "cornea_back"],
            "properties": {key: EXTRACTION_SCHEMA["properties"][key]
                           for key in ("document_type", "eye", "cornea_back")},
        }
        retry = core.openai_client().with_options(timeout=60, max_retries=0).responses.create(
            model=core.MODEL, store=False, reasoning={"effort": "medium"},
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": PROMPT + "\nFocused second reading of the SAME source. "
                 "The second image is its left-panel crop. Locate the Cornea Back heading in the "
                 "left-middle numeric panel below Cornea Front. Read each labeled row, including "
                 "any explicitly printed K1/K2 axes. Do not substitute Rh/Rv, Rf/Rs, "
                 "Rm, Rmin, anterior values or the map legend. If only one axis is printed, leave "
                 "the other null; do not invent or calculate it. Recheck all posterior K fields "
                 "for consistency, focusing on: " + ", ".join(missing)},
                {"type": "input_image", "image_url": core.data_url(raw, filename), "detail": "original"},
                {"type": "input_image", "image_url": core.data_url(output.getvalue(), "cornea-back-panel.png"), "detail": "original"},
            ]}],
            text={"verbosity": "low", "format": {"type": "json_schema", "name": "cerai_iol_cornea_back_reread", "strict": True, "schema": schema}},
        )
        reread = json.loads(retry.output_text)
        if reread.get("document_type") != result["document_type"] or reread.get("eye") != result["eye"]:
            logger.warning("IOL_CORNEA_BACK_REREAD rejected source_identity")
            return result
        candidate = reread.get("cornea_back") or {}
        # A disagreement on already-read measurements makes the reread ambiguous.
        if any(back.get(key) is not None and candidate.get(key) is not None
               and back[key] != candidate[key] for key in fields):
            logger.warning("IOL_CORNEA_BACK_REREAD rejected measurement_conflict")
            return result
        recovered = {}
        for key in missing:
            value = candidate.get(key)
            if value is None or isinstance(value, bool):
                continue
            try:
                recovered[key] = TypeAdapter(PosteriorCorneaInput.model_fields[key].rebuild_annotation()).validate_python(value, strict=True)
            except ValidationError:
                continue
        merged = {**back, **recovered}
        validated = complete_posterior_axes(merged)
        if all(validated.get(key) is not None for key in fields):
            PosteriorCorneaInput(eye=result["eye"], source="PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK", **validated)
        result["cornea_back"] = merged
        result["unreadable_fields"] = [key for key in result.get("unreadable_fields", [])
                                       if key not in {"cornea_back." + field for field in recovered}]
        logger.info("IOL_CORNEA_BACK_REREAD complete recovered=%s remaining=%s", ",".join(recovered),
                    ",".join(key for key in fields if merged.get(key) is None))
    except Exception as exc:
        # Keep successful primary transcription and the manual completion path.
        # No source image, patient name, measurements or API error payload in logs.
        logger.warning("IOL_CORNEA_BACK_REREAD failed error_type=%s", type(exc).__name__)
    return result
