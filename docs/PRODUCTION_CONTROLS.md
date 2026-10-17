# CER-AI production controls

Operational state reconciled on 17 October 2026. These controls do not change clinical decisions.

## Automated merge checks

Decision-critical paths are listed in `.github/CODEOWNERS`. The **Critical Change Review** workflow runs focused canonical, archive and IOL regression tests. It does not require a second person's approval; the owner removed that requirement.

The automated checks used before merging are:

- Canonical Runtime Safety / canonical-runtime (static checks, invariants and full regression suite)
- Canonical Runtime Safety / dependency-audit (production and development dependencies)
- Deep Import Isolation / test-file-isolation
- Critical Change Review / critical-regression for changes in its path filter

At this inspection, `main` was not protected by repository rules. These workflows run on pull requests, but GitHub does not enforce their success as a merge restriction. Check all applicable results before merging. Do not describe advisory checks as mandatory repository enforcement.

## Deployment gate

Production uses the Railway pre-deploy command `python scripts/verify_ci_before_deploy.py` with a 900-second Railway timeout. The script waits up to 600 seconds for the exact production commit's push runs of **Canonical Runtime Safety** and **Deep Import Isolation**. It fails closed if the commit, credentials, runs or successful conclusions cannot be verified. A failed gate blocks the new release; it does not replace the currently running deployment.

Railway's native source `checkSuites` setting was false at inspection. The pre-deploy script supplies the actual CI gate. Do not assume enabling native CI waiting or branch protection is necessary to satisfy a human-review requirement. Verify Railway deployment success, public software version, commit identity and `/health` after every release.

## Archive evidence

`python scripts/verify_case_archive.py` is the approved PHI-free encrypted write/read/list canary. Run it with Railway production variables and retain only its timestamp, digest, and byte count. Never store bucket credentials or patient identifiers in CI artifacts.

IOL source images use the existing encrypted case archive, bound to the doctor's assessment identifier. IOL snapshots and PDFs include software, independent IOL policy and deployment commit identities. Legacy snapshots without identity retain an explicit unknown value. Previously unarchived source images cannot be recovered retroactively.

ESCRS cloud transfer requires an explicit, versioned disclosure covering Browserless, the ESCRS IOL Calculator and the transmitted fields. Record consent before calling the provider and record the verified or failed outcome. Audit details contain fixed operational metadata, never clinical measurements, patient initials, provider tokens or session URLs. The audit callback must persist the consent; an unavailable audit prevents transfer.

## Performance evidence

The **Production SLO Evidence** workflow checks the homepage, `/health`, and the unauthenticated `/app` login redirect hourly. It fails if the homepage p95 across five probes exceeds 10 seconds. Railway HTTP logs remain authoritative for application-path p95/p99 and 5xx analysis.

## Configuration hygiene

Empty staged Railway environment patches carry no intended change and should be discarded. Review non-empty staged patches before acceptance.
