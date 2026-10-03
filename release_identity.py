"""Operational release identity; never participates in clinical decisions."""
from __future__ import annotations

import os
import re

SOFTWARE_VERSION = "2.0.1"


def deployment_sha() -> str | None:
    """Return a full Railway commit identity, or explicitly leave it unknown."""
    value = os.getenv("RAILWAY_GIT_COMMIT_SHA", "").strip()
    return value.lower() if re.fullmatch(r"[0-9a-fA-F]{40}", value) else None
