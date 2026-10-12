"""Canonical IOL page rendering for public and authenticated routes."""

from pathlib import Path

from .models import ASTIGMATISM_QUESTION_THRESHOLD_D


def render_iol_html() -> str:
    return Path("static/iol.html").read_text(encoding="utf-8").replace(
        "__ASTIGMATISM_THRESHOLD_D__", str(ASTIGMATISM_QUESTION_THRESHOLD_D)
    )
