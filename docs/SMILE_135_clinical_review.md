# SMILE device-maximum safety correction — clinical review required

Base reviewed: main on 2026-11-05. Related: #135. This draft must not be merged/deployed without independent medical review and surgeon signoff. It does not close all requirements of #135.

## Implemented behavior

- Every SMILE assessment requires a finite, positive, surgeon-entered VisuMax **maximum** lenticule thickness. Missing/invalid values yield ASSESSMENT INCOMPLETE; independent STOP-DEFER findings retain precedence. A central thickness must not be entered unless confirmed identical to the maximum.
- Legacy generic ablation/lenticule aliases cannot substitute for the explicit maximum field. Explicit theoretical/unknown provenance is rejected. The system records a surgeon transcription, not an independently verified device measurement.
- The existing spherical approximation is retained only as report metadata for zero-cylinder myopic correction: LT = 15 + 13 × |sphere| × (OZ/6)^2, model CERAI_SPHERICAL_LT_V1, fixed estimate edge 15 µm. It never supplies safety or ERSS tissue inputs. Cylinder cases have no supported maximum-LT estimate. Device input and the separate estimate remain visible together for spherical cases.
- Device input recomputes RSB and the existing cap-inclusive PTA. Refraction, OZ, cap or platform edits clear the old device depth, preventing reuse of a treatment plan for different settings. Reports are invalidated on form edits.
- SMILE RSB and PTA numeric stop rules remain unchanged, labelled institutional precautions. ERSS remains independent and explicitly LASIK-derived. BAD-D/NICE/PS3 and LASIK/PRK calculations are unchanged.
- The current implementation uses **thinnest pachymetry** for RSB and the cap-inclusive PTA denominator. It does not silently relabel this as measured CCT or substitute a different denominator.

## Evidence and limits

1. Santhiago et al., 2014, PMID 24727263: the PTA ≥40% association was studied in LASIK; it is not a validation of the same threshold in SMILE. https://pubmed.ncbi.nlm.nih.gov/24727263/
2. Ong et al., 2019, PMID 31686775: a retrospective series including 94 SMILE eyes reported no ectasia at three years, and explicitly called for procedure-specific safe PTA thresholds. It cannot establish a universally safe SMILE boundary. https://pubmed.ncbi.nlm.nih.gov/31686775/
3. PMID 27846649: retrospective SMILE comparison of 313 eyes below and 373 eyes at/above 40% PTA; absence of observed ectasia over the follow-up does not prove universal safety. https://pubmed.ncbi.nlm.nih.gov/27846649/
4. Evidence-Based Guidelines for Keratorefractive Lenticule Extraction Surgery, Ophthalmology, 2024 publication record: recommendations distinguish removed lenticule/CCT from LASIK cap-inclusive PTA. Reference RST/LT-index values are different metrics and are **not implemented by this patch**. https://www.aaojournal.org/article/S0161-6420(24)00724-3/fulltext

No manufacturer validation of the legacy 13 µm/D approximation is asserted.

## Required clinical decisions before production

- Approve the conservative policy requiring device maximum LT for **all** SMILE cases, including purely spherical low-risk cases. This is a completeness policy, not a new tissue cutoff.
- Approve wording and continued institutional use of the unchanged RSB 300 µm and cap-inclusive PTA 40% gates, ERSS limitations and thinnest-pachymetry denominator. Any numerical or metric change requires separate evidence review and surgeon approval.
- Issue #135 requests an explicit conservative borderline margin. No new numerical margin is introduced without that review. Universal device confirmation includes every borderline case without relying on an unapproved margin. If an estimate-only pathway is ever proposed, its margin must be specified, independently reviewed and tested before enabling that pathway.
- Review the fixed 15 µm estimate edge and absence of a validated cylinder model. Editable edge and a validated device/meridional model remain outside this safety correction; the reported edge is an estimate assumption, not a verified device setting.
- Confirm clinical acceptance using anonymized paired VisuMax 500/800 plans, including high cylinder and tissue-boundary cases. Synthetic regression tests verify software behavior, not clinical validity or device integration.

## QA

Initial regression reproduced PASS without device LT for cylinder 0, −1 and −5 D. Targeted tests cover missing/zero/negative/nonfinite values, unsupported provenance, device replacement, both platforms, OD/OS independence, unchanged PTA/RSB boundaries, independent STOP precedence, completion routing, source-preserving reports and Turkish translation. Full-suite and browser results are recorded in the PR.
