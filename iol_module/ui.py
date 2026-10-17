"""Canonical IOL page rendering for public and authenticated routes."""

from pathlib import Path
from hashlib import sha256
import re

from .models import ASTIGMATISM_QUESTION_THRESHOLD_D


def render_iol_html() -> str:
    html = Path("static/iol.html").read_text(encoding="utf-8").replace(
        "__ASTIGMATISM_THRESHOLD_D__", str(ASTIGMATISM_QUESTION_THRESHOLD_D)
    )
    return version_asset_urls(html)


def version_asset_urls(html: str) -> str:
    # Asset identity follows its bytes, so a release cannot reuse a stale script URL.
    return re.sub(
        r'(/static/[a-z0-9-]+\.(?:js|css))\?v=[^"\s]+',
        lambda match: match[1] + '?v=' + sha256(Path(match[1].lstrip('/')).read_bytes()).hexdigest()[:16],
        html,
    )
