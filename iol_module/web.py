"""HTTP boundary for the independent IOL module."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import Body, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError

import operational_security

from .engine import evaluate_case
from .extraction import extract_image, validate_source_bundle
from .lens_catalog import public_catalog
from .escrs_transfer import create_escrs_transfer
from .models import EscrsTransferInput, IOLCaseInput, IOLPowerPlanInput
from .power import plan_iol_power
from .report import IOLReportInput, build_iol_report
from .ui import render_iol_html


def install(core: Any) -> None:
    if getattr(core, "_cerai_iol_module_installed", False):
        return

    @core.app.get("/iol", include_in_schema=False)
    def iol_page():
        return HTMLResponse(
            render_iol_html(),
            headers={"Cache-Control": "no-store"},
        )

    @core.app.post("/iol/extract")
    async def iol_extract(
        images: list[UploadFile] = File(...),
        patient_name: str | None = Form(None),
        assessment_request_id: str | None = Form(None),
    ):
        current_principal = getattr(core, "_cerai_current_principal", None)
        principal = current_principal() if callable(current_principal) else None
        if principal is None:
            from user_access import current_principal as bound_principal
            principal = bound_principal()
        if principal is not None and principal.access_plan == "DEMO" and not str(assessment_request_id or "").strip():
            raise HTTPException(422, "Demo IOL assessment identifier is required.")
        assert_demo_credit = getattr(core, "_cerai_assert_demo_credit", None)
        if principal is not None and callable(assert_demo_credit):
            assert_demo_credit(principal.user_id)
        if len(images) not in {3, 5}:
            raise HTTPException(422, "Upload 3 images for one eye or 5 for both eyes: Cataract Pre-Op and 4 Maps Refractive for each eye, plus one shared IOLMaster 500 report.")
        payloads = await operational_security.read_uploads(images)
        return await process_sources(payloads, principal, assessment_request_id, patient_name)

    async def process_sources(payloads, principal, assessment_request_id, patient_name, progress=None):
        slots = asyncio.Semaphore(2)
        completed = 0
        async def read_source(raw, filename):
            nonlocal completed
            async with slots:
                try:
                    result = await asyncio.to_thread(extract_image, core, raw, filename)
                except Exception as exc:
                    raise HTTPException(502, f"Unable to transcribe {filename}.") from exc
                completed += 1
                if progress:
                    progress("READING", completed)
                return {"filename": filename, "extraction": result}
        results = await asyncio.gather(*(read_source(raw, filename) for raw, filename in payloads), return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                raise result
        try:
            identity = validate_source_bundle(
                results,
                surgeon_patient_name=patient_name,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        from .archive import archive_iol_sources
        if progress:
            progress("ARCHIVING", len(payloads))
        source_archive = await asyncio.to_thread(
            archive_iol_sources, core, payloads, results, principal, assessment_request_id, patient_name,
        )
        consume_demo_credit = getattr(core, "_cerai_consume_demo_credit", None)
        if principal is not None and callable(consume_demo_credit):
            consume_demo_credit(
                principal.user_id,
                str(assessment_request_id or "iol-full-account"),
                "IOL",
            )
        return {"sources": results, "identity": identity, "source_archive": source_archive}

    from .jobs import install as install_jobs
    install_jobs(core, process_sources)

    @core.app.post("/iol/evaluate")
    def iol_evaluate(payload: dict[str, Any] = Body(...)):
        try:
            case = IOLCaseInput.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        return evaluate_case(case).model_dump(mode="json")

    @core.app.get("/iol/lenses")
    def iol_lenses():
        return {"lenses": public_catalog()}

    @core.app.post("/iol/power/plan")
    def iol_power_plan(payload: dict[str, Any] = Body(...)):
        try:
            case = IOLPowerPlanInput.model_validate(payload)
            return plan_iol_power(case).model_dump(mode="json")
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @core.app.post("/iol/report/pdf")
    def iol_report_pdf(payload: dict[str, Any] = Body(...)):
        try:
            report_payload = dict(payload)
            assessment_request_id = report_payload.pop("assessment_request_id", None)
            report = IOLReportInput.model_validate(report_payload)
            current_principal = getattr(core, "_cerai_current_principal", None)
            principal = current_principal() if callable(current_principal) else None
            if principal is None:
                from user_access import current_principal as bound_principal
                principal = bound_principal()
            from .archive import archive_iol_report
            pdf, archive_headers = archive_iol_report(core, report, principal, assessment_request_id)
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return Response(pdf, media_type="application/pdf", headers={
            **archive_headers,
            "Cache-Control": "no-store", "Content-Disposition": 'inline; filename="cerai-iol-report.pdf"',
            "X-Content-Type-Options": "nosniff",
        })

    @core.app.post("/iol/escrs-transfer")
    def iol_escrs_transfer(payload: dict[str, Any] = Body(...)):
        try:
            case = EscrsTransferInput.model_validate(payload)
            return create_escrs_transfer(case)
        except ValidationError as exc:
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc

    @core.app.get("/iol/escrs-cloud-config")
    def iol_escrs_cloud_config():
        import os
        from user_access import require_current_principal
        from .escrs_cloud import cloud_provider, model_names
        require_current_principal()
        provider = cloud_provider()
        key = 'BROWSERBASE_API_KEY' if provider == 'browserbase' else 'BROWSERLESS_TOKEN'
        from .escrs_local import executable
        enabled = bool(executable()) if provider == "local" else bool(os.environ.get(key, "").strip())
        return {"enabled": enabled, "models": model_names(), 'provider':provider}

    @core.app.post("/iol/escrs-cloud-transfer")
    def iol_escrs_cloud_transfer(payload: dict[str, Any] = Body(...)):
        from user_access import require_current_principal
        from .escrs_cloud import CloudEye, CloudTransfer, cloud_provider, create_cloud_transfer
        principal = require_current_principal()
        try:
            # The signed-in doctor's identity is authoritative.
            case = CloudTransfer.model_validate({**payload, "surgeon": principal.display_name})
        except ValidationError as exc:
            allowed = set(CloudTransfer.model_fields) | set(CloudEye.model_fields)
            fields = sorted({part for error in exc.errors() for part in error['loc']
                             if isinstance(part, str) and part in allowed})
            logging.getLogger(__name__).warning('ESCRS transfer validation rejected fields: %s', ','.join(fields))
            raise HTTPException(422, detail=json.loads(exc.json(include_url=False))) from exc
        provider = cloud_provider()
        if case.provider != provider or (provider in {'browserbase', 'local'} and case.consent_version != 'ESCRS-CLOUD-2026-10-17-V2'):
            raise HTTPException(409, 'The ESCRS provider changed. Reload CER-AI and accept the current disclosure.')
        audit = getattr(core, '_cerai_audit_event', None)
        if not callable(audit):
            raise HTTPException(503, 'Transfer audit is unavailable. Please retry.')
        # Fixed metadata only: never include the request, measurements or viewer URL.
        receipt = audit('ESCRS_TRANSFER_CONSENT', actor=principal,
              details={'consent_version': case.consent_version,
                       'recipients': (['ESCRS IOL Calculator'] if provider == 'local' else ['Browserbase' if provider == 'browserbase' else 'Browserless', 'ESCRS IOL Calculator'])})
        if receipt is None:
            raise HTTPException(503, 'Transfer consent could not be recorded. Please retry.')
        try:
            if provider == 'local':
                from .escrs_local import create_local_transfer
                result = create_local_transfer(case, principal.user_id)
            elif provider == 'browserbase':
                from .escrs_browserbase import create_browserbase_transfer
                result = create_browserbase_transfer(case, principal.user_id)
            else:
                result = create_cloud_transfer(case, principal.user_id)
        except HTTPException as exc:
            audit('ESCRS_TRANSFER_OUTCOME', actor=principal,
                  details={'status': 'FAILED', 'http_status': exc.status_code})
            raise
        audit('ESCRS_TRANSFER_OUTCOME', actor=principal, details={'status': 'VERIFIED'})
        return result

    from .escrs_browserbase import install as install_browserbase_sessions
    install_browserbase_sessions(core)
    from .escrs_local import install as install_local_sessions
    install_local_sessions(core)
    core._cerai_iol_module_installed = True
