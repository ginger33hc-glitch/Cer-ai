"""Persist IOL report snapshots in the shared encrypted, role-scoped case archive."""
from datetime import datetime
from uuid import uuid4, uuid5, NAMESPACE_URL
from zoneinfo import ZoneInfo

from fastapi import HTTPException

import case_catalog
from .report import IOLReportInput, build_iol_report


def build_archived_iol_pdf(snapshot):
    payload = dict(snapshot['iol_report'])
    payload['locale'] = snapshot.get('locale', 'en')
    return build_iol_report(IOLReportInput.model_validate(payload),
                            snapshot['patient']['reviewer'],
                            report_date=snapshot['patient']['report_date'])


def archive_iol_report(core, report, actor, assessment_request_id=None):
    runtime = getattr(core, '_cerai_case_archive_runtime', None)
    if runtime is None or not runtime.enabled:
        return build_iol_report(report, getattr(actor, 'display_name', '')), {}
    if actor is None:
        raise HTTPException(401, 'Sign in to archive the IOL report.')
    request_id = str(assessment_request_id or uuid4())
    if not 1 <= len(request_id) <= 128:
        raise ValueError("Invalid IOL assessment identifier.")
    case_id = uuid5(NAMESPACE_URL, f'cerai:iol:{actor.user_id}:{request_id}').hex
    clinical = report.model_dump(mode='json')
    clinical.pop('locale', None)
    ready = {
        'module': 'IOL',
        'patient': {'name': report.patient_name, 'age': report.patient_age_years,
                    'reviewer': actor.display_name,
                    'report_date': datetime.now(ZoneInfo('Europe/Istanbul')).date().isoformat()},
        'decision': {'status': 'IOL', 'action': 'IOL surgical plan',
                     'eyes': [{'eye': eye.eye, 'status': eye.plan.calculation_status} for eye in report.eyes]},
        'iol_report': clinical,
    }
    try:
        archive = runtime.archive
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
