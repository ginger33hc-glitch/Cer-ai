"""Verified ESCRS form handoff through a short-lived Browserless session."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from fastapi import HTTPException
from pydantic import Field, StrictBool, StrictInt, model_validator

from .lens_catalog import get_lens
from .models import EscrsEyeInput, PriorCornealSurgery, StrictModel

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"production-sfo.browserless.io", "production-ams.browserless.io", "production-lon.browserless.io"}
SESSION_SECONDS = 120
_lock = Lock()
_leases: dict[str, float] = {}


def model_names() -> dict[str, str]:
    return json.loads((ROOT / "static/escrs-models.json").read_text())


class CloudEye(EscrsEyeInput):
    toric: StrictBool
    lens_id: str
    lens_matches: list[str] = Field(min_length=1, max_length=1)
    manufacturer_matches: list[str] = Field(min_length=1, max_length=1)
    target_refraction_d: float = Field(ge=-20, le=20, allow_inf_nan=False)
    a_constant: float = Field(ge=100, le=130, allow_inf_nan=False)
    incision_axis_deg: float | None = Field(default=None, ge=0, le=180)
    sia_d: float | None = Field(default=None, ge=0, le=5)

    @model_validator(mode="after")
    def verify_model(self):
        lens = get_lens(self.lens_id)
        name = model_names().get(self.lens_id)
        if lens is None or name is None or self.lens_matches != [name]:
            raise ValueError("This lens has no verified ESCRS model mapping. No substitute selected.")
        manufacturer = "Johnson and Johnson Vision" if lens.manufacturer == "Johnson & Johnson" else lens.manufacturer
        if self.manufacturer_matches != [manufacturer]:
            raise ValueError("ESCRS manufacturer does not match the selected lens.")
        if self.toric != ("toric" in (lens.subtype or "").lower()):
            raise ValueError("ESCRS Toric mode must match the selected lens family.")
        if self.prior_corneal_surgery != PriorCornealSurgery.NONE:
            raise ValueError("Post-refractive automatic transfer has not been validated.")
        if self.toric and any(v is None for v in (self.k1_axis_deg, self.k2_axis_deg, self.incision_axis_deg, self.sia_d)):
            raise ValueError("Review the toric axes, incision and SIA before transfer.")
        return self


class CloudTransfer(StrictModel):
    version: Literal[1]
    initials: str = Field(min_length=1, max_length=12)
    age: StrictInt = Field(ge=1, le=120)
    sex: Literal["Male", "Female"]
    surgeon: str = Field(min_length=1, max_length=160)
    terms_accepted: Literal[True]
    data_transfer_accepted: Literal[True]
    consent_version: Literal["ESCRS-BROWSERLESS-2026-10-17"]
    eyes: dict[Literal["OD", "OS"], CloudEye] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def only_initials(self):
        if not self.initials.isalpha():
            raise ValueError("Send patient initials only.")
        return self


def build_query(case: CloudTransfer) -> str:
    payload = case.model_dump(mode="json", exclude={"terms_accepted", "data_transfer_accepted", "consent_version"})
    adapter = (ROOT / "extensions/escrs-assistant/adapter.js").read_text()
    code = adapter + "\nreturn JSON.stringify(await globalThis.CeraiEscrsAdapter.run(" + json.dumps(payload, ensure_ascii=True) + "));"
    consent = "[...document.querySelectorAll('button')].find(b=>b.textContent.trim().toUpperCase()==='I AGREE')"
    return (
        'mutation CeraiTransfer { goto(url:"https://iolcalculator.escrs.org/") { status } '
        f'click(selector:{json.dumps(consent)},timeout:45000) {{ time }} '
        'waitForSelector(selector:"input",timeout:20000) { time } '
        f'verify:evaluate(content:{json.dumps(code)},timeout:60000) {{ value }} '
        'liveURL(detached:true,timeout:90000,interactable:true,resizable:true) { liveURL } '
        'reconnect(timeout:90000) { browserWSEndpoint } }'
    )


def create_cloud_transfer(case: CloudTransfer, user_id: str) -> dict:
    token = os.environ.get("BROWSERLESS_TOKEN", "").strip()
    host = os.environ.get("BROWSERLESS_HOST", "production-sfo.browserless.io")
    if not token or host not in HOSTS:
        raise HTTPException(503, "ESCRS cloud transfer is unavailable.")
    now = monotonic()
    with _lock:
        for key in list(_leases):
            if _leases[key] <= now:
                del _leases[key]
        if user_id in _leases or len(_leases) >= 2:
            raise HTTPException(429, "An ESCRS cloud session is still active. Wait up to two minutes before retrying.", headers={"Retry-After": "120"})
        _leases[user_id] = now + SESSION_SECONDS
    try:
        request = Request(
            "https://" + host + "/chromium/bql?" + urlencode({"token": token, "timeout": SESSION_SECONDS * 1000}),
            data=json.dumps({"query": build_query(case)}).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urlopen(request, timeout=125) as response:
            result = json.loads(response.read(512 * 1024))
        if result.get("errors"):
            raise ValueError("Field verification or session creation failed")
        data = result["data"]
        selected = json.loads(data["verify"]["value"])
        expected = {side: eye.lens_matches[0] for side, eye in case.eyes.items()}
        if selected != expected or not data["reconnect"].get("browserWSEndpoint"):
            raise ValueError("Unexpected ESCRS verification result")
        url = data["liveURL"]["liveURL"]
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != host or parsed.port not in {None, 443} or parsed.username or parsed.password or "/live/" not in parsed.path:
            raise ValueError("Invalid viewer address")
        # Return only the expiring viewer link; never return API or reconnect keys.
        return {"escrs_url": url, "verified": True, "session_limit_seconds": SESSION_SECONDS}
    except Exception as exc:
        with _lock:
            _leases.pop(user_id, None)
        if isinstance(exc, HTTPError) and exc.code == 429:
            raise HTTPException(429, "ESCRS cloud capacity is busy. Try again shortly.") from None
        raise HTTPException(502, "ESCRS cloud transfer could not be verified. No completed session was opened.") from None
