"""Operational provenance only; never changes IOL calculations."""
from release_identity import SOFTWARE_VERSION, deployment_sha

IOL_POLICY_VERSION = "CER-AI-IOL-2026-10-17-SOURCE-ARCHIVE-V1"


def current_versions() -> dict:
    return {"software": SOFTWARE_VERSION, "clinical_policy": IOL_POLICY_VERSION,
            "deployment_sha": deployment_sha()}
