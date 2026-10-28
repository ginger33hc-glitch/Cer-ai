"""Persist screening sources and result through the existing encrypted archive."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
import case_catalog
from .report import build_screening_pdf


def archive_screening(core, result, payloads, actor, case_id):
    runtime = getattr(core, "_cerai_case_archive_runtime", None)
    if runtime is None or not runtime.enabled:
        if runtime is not None and runtime.required:
            raise HTTPException(503, "Required screening archive unavailable.")
        return None
    if actor is None:
        raise HTTPException(401, "Sign in to archive the screening case.")
    snapshot = dict(result)
    snapshot["patient"] = {
        **result.get("patient", {}),
        "reviewer": actor.display_name,
        "report_date": datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat(),
    }
    statuses = {eye["screening_result"] for eye in result["eyes"]}
    overall = next(
        status
        for status in ("NOT_ASSESSABLE", "POSITIVE", "SUSPICIOUS", "NEGATIVE")
        if status in statuses
    )
    snapshot["decision"] = {
        "status": overall,
        "action": "Keratoconus screening",
        "eyes": [
            {"eye": e["eye"], "status": e["screening_result"]} for e in result["eyes"]
        ],
    }
    try:
        archive = runtime.archive
        archive.archive_sources(
            case_id,
            payloads,
            patient_metadata={**snapshot["patient"], "created_by": actor.user_id},
            extracted=snapshot,
        )
        sources = archive.list_sources(case_id)
        if len(sources) != len(payloads) or any(
            archive.get_bytes(item.artifact) != raw
            for item, (raw, _) in zip(sources, payloads)
        ):
            raise RuntimeError("Screening source readback mismatch")
        revision = archive.archive_ready(
            case_id, snapshot, pdf_builder=build_screening_pdf
        )
        case_catalog.write_entry(archive, revision, snapshot, actor=actor)
        audit = getattr(core, "_cerai_audit_event", None)
        if callable(audit):
            audit(
                "CASE_ARCHIVED",
                actor=actor,
                case_id=case_id,
                revision_id=revision.revision_id,
                details={"module": "KERATOCONUS"},
            )
        return {
            "status": "ARCHIVED",
            "case_id": case_id,
            "revision_id": revision.revision_id,
        }
    except Exception as exc:
        runtime._log_failure("keratoconus", "persist_and_index", exc)
        raise HTTPException(
            503, "Screening could not be archived. Please retry."
        ) from exc
