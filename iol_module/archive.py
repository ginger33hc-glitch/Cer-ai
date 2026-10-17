"""Persist IOL report snapshots in the shared encrypted, role-scoped case archive."""
from datetime import datetime
from uuid import uuid4, uuid5, NAMESPACE_URL
from zoneinfo import ZoneInfo
from hashlib import sha256

from fastapi import HTTPException

import case_catalog
from .report import IOLReportInput, build_iol_report
from .provenance import current_versions


def iol_case_id(actor, assessment_request_id):
    if actor is None:
        raise HTTPException(401, 'Sign in to archive the IOL case.')
    request_id = str(assessment_request_id or uuid4())
    if not 1 <= len(request_id) <= 128:
        raise ValueError("Invalid IOL assessment identifier.")
    return uuid5(NAMESPACE_URL, f'cerai:iol:{actor.user_id}:{request_id}').hex


def archive_iol_sources(core, payloads, extracted, actor, assessment_request_id, patient_name):
    runtime = getattr(core, '_cerai_case_archive_runtime', None)
    if runtime is None or not runtime.enabled:
        if runtime is not None and runtime.required:
            raise HTTPException(503, 'Required IOL source archive is unavailable.')
        return None
    if not assessment_request_id:
        raise HTTPException(422, 'IOL assessment identifier is required to archive source images.')
    case_id = iol_case_id(actor, assessment_request_id)
    try:
        existing = runtime.archive.list_sources(case_id)
        expected = [(name, sha256(raw).hexdigest()) for raw, name in payloads]
        if existing:
            actual = [(item.original_filename, item.artifact.sha256) for item in existing]
            if actual != expected:
                raise HTTPException(409, 'Source images changed. Start a new IOL assessment.')
        else:
            runtime.archive.archive_sources(
                case_id, payloads,
                patient_metadata={'name': patient_name, 'created_by': actor.user_id},
                extracted={'module': 'IOL', 'sources': extracted, 'versions': current_versions()},
            )
        sources = runtime.archive.list_sources(case_id)
        if len(sources) != len(payloads):
            raise RuntimeError('Incomplete IOL source archive')
        for item, (raw, _) in zip(sources, payloads):
            if runtime.archive.get_bytes(item.artifact) != raw:
                raise RuntimeError('IOL source archive readback mismatch')
        return {'status': 'ARCHIVED', 'case_id': case_id, 'count': len(sources)}
    except HTTPException:
        raise
    except Exception as exc:
        runtime._log_failure('iol_sources', 'persist_and_verify', exc)
        raise HTTPException(503, 'IOL source images could not be archived. Please retry.') from exc


def build_archived_iol_pdf(snapshot):
    payload = dict(snapshot['iol_report'])
    payload['locale'] = snapshot.get('locale', 'en')
    return build_iol_report(IOLReportInput.model_validate(payload),
                            snapshot['patient']['reviewer'],
                            report_date=snapshot['patient']['report_date'],
                            versions=snapshot.get('versions', {}))


def archive_iol_report(core, report, actor, assessment_request_id=None):
    runtime = getattr(core, '_cerai_case_archive_runtime', None)
    if runtime is None or not runtime.enabled:
        if runtime is not None and runtime.required:
            raise HTTPException(503, 'Required IOL report archive is unavailable.')
        return build_iol_report(report, getattr(actor, 'display_name', '')), {}
    case_id = iol_case_id(actor, assessment_request_id)
    clinical = report.model_dump(mode='json')
    clinical.pop('locale', None)
    ready = {
        'module': 'IOL',
        'versions': current_versions(),
        'patient': {'name': report.patient_name, 'age': report.patient_age_years,
                    'reviewer': actor.display_name,
                    'report_date': datetime.now(ZoneInfo('Europe/Istanbul')).date().isoformat()},
        'decision': {'status': 'IOL', 'action': 'IOL surgical plan',
                     'eyes': [{'eye': eye.eye, 'status': eye.plan.calculation_status} for eye in report.eyes]},
        'iol_report': clinical,
    }
    try:
        archive = runtime.archive
        ready['source_artifacts'] = [
            {'ordinal': item.ordinal, 'filename': item.original_filename,
             'sha256': item.artifact.sha256}
            for item in archive.list_sources(case_id)
        ]
        revision_id = archive.revision_id_for(ready)
        existing = case_catalog.get_entry(archive, case_id, revision_id)
        if existing is None:
            revision = archive.archive_ready(case_id, ready, pdf_builder=build_archived_iol_pdf)
            case_catalog.write_entry(archive, revision, ready, actor=actor)
            audit = getattr(core, '_cerai_audit_event', None)
            if callable(audit):
                audit('CASE_ARCHIVED', actor=actor, case_id=case_id, revision_id=revision_id,
                      details={'module': 'IOL'})
        ref = archive.find_report(case_id, revision_id, report.locale, 'pdf')
        if ref is None:
            raise RuntimeError('Archived IOL PDF missing')
        pdf = archive.get_bytes(ref)
        return pdf, {'X-CERAI-Archive-Status': 'ARCHIVED',
                     'X-CERAI-Case-ID': case_id, 'X-CERAI-Revision-ID': revision_id}
    except Exception as exc:
        runtime._log_failure('iol_report', 'persist_and_index', exc)
        # Never label an unpersisted report as ready when archiving is enabled.
        raise HTTPException(503, 'IOL report could not be archived. Please retry.') from exc
