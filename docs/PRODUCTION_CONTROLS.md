# CER-AI production controls

This document records controls added after the 10 October 2026 production audit.

## Merge controls

Decision-critical paths are listed in `.github/CODEOWNERS`. The **Critical Change Review** workflow requires an approving review from someone other than the pull-request author and runs focused canonical, archive, and IOL regression tests.

For enforcement, repository rules must require pull requests and these status checks on `main`:

- Canonical Runtime Safety / canonical-runtime
- Canonical Runtime Safety / dependency-audit
- Deep Import Isolation / test-file-isolation
- Critical Change Review / independent-review
- Critical Change Review / critical-regression

Dismiss stale approvals when new commits are pushed and block direct pushes.

## Deployment gate

Production deploys must wait for required GitHub checks. Railway's source-deploy setting should be configured to wait for CI before deployment. The public service must still be verified after every release.

## Archive evidence

`python scripts/verify_case_archive.py` is the approved PHI-free encrypted write/read/list canary. Run it with Railway production variables and retain only its timestamp, digest, and byte count. Never store bucket credentials or patient identifiers in CI artifacts.

## Performance evidence

The **Production SLO Evidence** workflow checks the homepage, `/health`, and the unauthenticated `/app` login redirect hourly. It fails if the homepage p95 across five probes exceeds 10 seconds. Railway HTTP logs remain authoritative for application-path p95/p99 and 5xx analysis.

## Configuration hygiene

Empty staged Railway environment patches carry no intended change and should be discarded. Non-empty staged patches require review before acceptance.
