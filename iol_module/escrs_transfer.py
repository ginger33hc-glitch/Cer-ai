"""De-identified BiomPIN handoff to the ESCRS IOL Calculator."""

from __future__ import annotations

import json
import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .models import EscrsTransferInput


BIOMAPI_PROCESS_URL = os.getenv(
    "BIOMAPI_PROCESS_URL", "https://biomapi.com/api/v1/biom/process"
)
ESCRS_IOL_CALCULATOR_URL = "https://iolcalculator.escrs.org/"


def _eye_data(eye) -> dict[str, object]:
    if eye is None:
        return {}
    data: dict[str, object] = {
        "lens_status": "Phakic",
        "AL": eye.axial_length_mm,
        "ACD": eye.acd_mm,
        "K1_magnitude": eye.k1_d,
        "K2_magnitude": eye.k2_d,
        "keratometric_index": 1.3375,
    }
    for field, value in (("K1_axis", eye.k1_axis_deg), ("K2_axis", eye.k2_axis_deg)):
        if value is not None:
            data[field] = int(value)
    if eye.prior_corneal_surgery is not None:
        data["post_refractive"] = {
            "NONE": "None", "MYOPIC_LASIK_PRK": "Myopic LVC",
            "HYPEROPIC_LASIK_PRK": "Hyperopic LVC", "RK": "Radial Keratotomy",
        }[eye.prior_corneal_surgery.value]
    if eye.lens_thickness_mm is not None:
        data["LT"] = eye.lens_thickness_mm
    if eye.cct_um is not None:
        data["CCT"] = int(eye.cct_um)
    if eye.wtw_mm is not None:
        data["WTW"] = eye.wtw_mm
    return data


def build_biomdirect(case: EscrsTransferInput) -> dict[str, object]:
    return {
        "data": {
            "biometer": {"device_name": "Other", "manufacturer": "Other"},
            "patient": {"gender": case.biological_sex},
            "right_eye": _eye_data(case.right_eye),
            "left_eye": _eye_data(case.left_eye),
        },
        "extra_data": {
            "notes": (
                "CER-AI composite source: AL, K and ACD from IOLMaster 500; "
                "CCT and WTW from Pentacam Cataract Pre-Op. "
                "Verify every imported "
                "value before calculation."
            )
        },
    }


def _multipart(document: dict[str, object]) -> tuple[bytes, str]:
    boundary = f"----CerAiBiomAPI{uuid.uuid4().hex}"
    file_data = json.dumps(document, separators=(",", ":")).encode("utf-8")
    body = b"".join(
        (
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="cerai-escrs.json"\r\n',
            b"Content-Type: application/json\r\n\r\n",
            file_data,
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="biompin"\r\n\r\ntrue\r\n',
            f"--{boundary}--\r\n".encode(),
        )
    )
    return body, f"multipart/form-data; boundary={boundary}"


def create_escrs_transfer(case: EscrsTransferInput) -> dict[str, str | None]:
    body, content_type = _multipart(build_biomdirect(case))
    headers = {
        "Content-Type": content_type,
        "Accept": "application/json",
        "User-Agent": "CER-AI-IOL/1.0",
        "X-BiomAPI-Integrator-ID": "cer-ai",
    }
    api_key = os.getenv("BIOMAPI_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(BIOMAPI_PROCESS_URL, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BiomAPI rejected the ESCRS transfer ({exc.code}): {detail[:300]}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("BiomAPI could not be reached for the ESCRS transfer.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("BiomAPI returned an invalid response for the ESCRS transfer.") from exc

    biompin = result.get("biompin") if isinstance(result, dict) else None
    pin = biompin.get("pin") if isinstance(biompin, dict) else None
    if not isinstance(pin, str) or not pin.strip():
        raise RuntimeError("BiomAPI did not return a BiomPIN for the ESCRS transfer.")
    expires_at = biompin.get("expires_at") if isinstance(biompin.get("expires_at"), str) else None
    return {
        "escrs_url": f"{ESCRS_IOL_CALCULATOR_URL}?biompin={quote(pin.strip())}",
        "expires_at": expires_at,
    }
