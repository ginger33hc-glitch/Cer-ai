# CER-AI Keratoconus Screening

Entry: `/keratoconus` from the clinical module selector. The protected POST
`/keratoconus/analyze` and `/keratoconus/stream` require surgeon-entered patient
name and whole-year age (1–120), bilateral manifest sphere, signed cylinder, axis,
and exactly five existing Pentacam sources. Surgeon-entered name and age use the
existing image-authority path and are retained in the result and archived PDF;
age is demographic context, not an added screening score. There is no procedure selection,
intended treatment, ablation, flap/cap, optical zone, RSB/RST, or PTA input.

The original image extraction, mandatory source identification, canonical source
locks, targeted rereading, geometric SRAX and post-merge validation are shared.
Screening does not invoke the surgical workflow or invent a surgical plan.

## Decision contract

The existing `canonical_runtime_service.evaluate_case` is the single runtime entry,
with the explicit `assessment_mode="KERATOCONUS"` path. It normalizes the same
source data and calls `clinical_core.keratoconus.evaluate_keratoconus` directly.
There is no screen-specific clinical runtime, wrapper, monkey patch, fallback
scorer or post-core decision override. The existing final disposition owner
supports explicit incomplete-first screening; its default surgical behavior is
unchanged. Canonical startup invariants verify direct ownership and routing.
Existing BAD-D classification, NICE scoring, I-S/SRAX topography component and PS3
factor evaluation are reused directly. No Pentacam index is reconstructed.

- PASS → NEGATIVE.
- CAUTION / PASS WITH CAUTION → SUSPICIOUS.
- STOP-DEFER → POSITIVE.
- Missing decision-critical dependencies, source conflicts or unverified identity
  → NOT_ASSESSABLE. Incomplete data is never a completed positive/negative result.

The ERSS **topography component** uses the existing component/disposition helpers;
it is explicitly not the full ERSS surgical total. Age, refractive magnitude and
residual bed components are excluded. PS3's common defer rule (one High or two
Moderate factors) is reused; one Moderate factor maps to Suspicious without
choosing a procedure. Procedure-specific allowances and the LASIK isolated
thickness exception are not applied. Existing thresholds and surgical outputs
are unchanged. Acquisition-quality warnings remain governed by the existing
non-blocking quality policy; unreadable critical measurements remain incomplete.

This owner-requested reuse of screening rules is not independent clinical
validation of a keratoconus diagnostic classifier or a probability estimate.
Positive screening is not a diagnosis; negative screening does not exclude
keratoconus. Missing SRAX confirmation or PS3 exception confirmation is reported
as a missing dependency; it is never assumed negative to force a result.

## Reporting and access

Results retain per-eye findings, missing dependencies, measurements, refraction,
source provenance, original source contexts and software/policy versions.
When the existing encrypted archive is enabled, source images are persisted and
read back, bilingual PDF snapshots are stored, and a role-scoped catalog entry is
created before returning success. Required archive failure is not silently
ignored. Owner access to another doctor's case uses the existing de-identification
boundary; PDFs regenerate from the de-identified snapshot.

The UI has English/Turkish labels, mobile layout, safe text rendering, print and
archived PDF access. Editing source data invalidates the displayed report. Inputs
are locked during an assessment; clinical data is not written to browser storage.
The existing named-user gate, request size limits, cost/concurrency guards and
demo-credit boundary apply.

## Progress transport

The UI reads newline-delimited JSON from the protected `/keratoconus/stream`
endpoint. Existing canonical progress publications drive milestone percentages:
upload accepted 10%, primary image reads 10–60% by completed image count,
verification 70%, assessment 85%, archiving 95%, result delivered 100%.
These are stage milestones, not elapsed-time estimates or clinical confidence.
There is no timer-based simulated increment. Error or truncated streams do not
produce a successful 100% state. The stream uses a request-local progress sink,
never a clinical wrapper or monkey patch. Patient data is not included in
progress events. Disconnects cancel the request task; no global progress state
or shared patient job is exposed.

## Verification

`tests/test_keratoconus.py` exercises canonical boundaries, surgical-field
independence, missing/conflicting data, source pipeline reuse, input validation,
protected transport, encrypted archive readback and owner de-identification.
`tests/test_keratoconus_browser.py` provides synthetic desktop English and mobile
Turkish browser scenarios with a stubbed server result; no clinical image or live
model call is used. Set `CERAI_CHROMIUM_EXECUTABLE` to run with a local Chromium.
