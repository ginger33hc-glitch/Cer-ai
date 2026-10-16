"""Local, synthetic-only proof of concept. Not registered in the CER-AI app.

Run from repository root with: uvicorn experiments.escrs_cloud.server:app
No real-patient upload endpoint, persistence or automatic calculation.
Browserless credentials stay in the server environment.
"""
import asyncio
import contextlib
import json
import os
from urllib.parse import urlencode, urlparse
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
TARGET = "https://iolcalculator.escrs.org/"
TTL = 120
WIDTH, HEIGHT = 390, 750
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
# Developer-only single viewer. A production service needs doctor authentication,
# per-session authorization, capacity limits and independently isolated workers.
TOKEN = secrets.token_urlsafe(32)
slot = asyncio.Lock()


def synthetic_case():
    eye = dict(toric=True, axial_length_mm=23.5, acd_mm=3.1, k1_d=42.5,
               k2_d=44, k1_axis_deg=15, k2_axis_deg=105, cct_um=550,
               lens_thickness_mm=4.3, wtw_mm=11.8, incision_axis_deg=180,
               sia_d=0.25, target_refraction_d=-0.25, a_constant=119.1,
               prior_corneal_surgery="NONE", manufacturer_matches=["Alcon"],
               lens_matches=["Clareon PanOptix Toric CNWTT2-6"])
    return dict(version=1, surgeon="CER-AI SYNTHETIC TEST", initials="TEST",
                age=61, sex="Female", eyes={"OD": eye, "OS": {
                    **eye, "toric": False, "axial_length_mm": 24.2,
                    "acd_mm": 3.6, "k1_d": 43, "k2_d": 44.5,
                    "cct_um": 540, "lens_thickness_mm": 4.1, "wtw_mm": 12,
                    "target_refraction_d": -0.5, "a_constant": 119.3,
                    "manufacturer_matches": ["Johnson and Johnson Vision"],
                    "lens_matches": ["DEN00V"]}})


def authorize(ws):
    return (ws.cookies.get("cloud_demo") == TOKEN
            and ws.headers.get("origin") in {
                "http://" + ws.headers.get("host", ""),
                "https://" + ws.headers.get("host", "")})



@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    response = HTMLResponse((Path(__file__).parent / "viewer.html").read_text())
    response.set_cookie("cloud_demo", TOKEN, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https", max_age=TTL)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


async def session(ws):
    async with async_playwright() as pw:
        token = os.environ.get("BROWSERLESS_TOKEN", "")
        if not token:
            raise RuntimeError("BROWSERLESS_TOKEN is not configured")
        host = os.environ.get("BROWSERLESS_HOST", "production-ams.browserless.io")
        if host not in {"production-ams.browserless.io", "production-lon.browserless.io", "production-sfo.browserless.io"}:
            raise ValueError("Unsupported Browserless host")
        endpoint = "wss://" + host + "/chromium/stealth?" + urlencode({"token": token, "timeout": TTL * 1000})
        browser = await pw.chromium.connect_over_cdp(endpoint)
        try:
            context = await browser.new_context(viewport={"width": WIDTH, "height": HEIGHT},
                                                is_mobile=True, has_touch=True)
            page = await context.new_page()
            await page.goto(TARGET, wait_until="domcontentloaded", timeout=45000)
            lock = asyncio.Lock()

            cdp = await context.new_cdp_session(page)
            live = await cdp.send("Browserless.liveURL", {
                "timeout": TTL * 1000, "interactable": True,
                "resizable": True, "showBrowserInterface": True,
            })
            live_url = live.get("liveURL", "")
            parsed = urlparse(live_url)
            if live.get("error") or parsed.scheme != "https" or parsed.hostname != host or parsed.username or parsed.password:
                raise RuntimeError("Invalid Browserless viewer URL")
            await ws.send_json({"liveURL": live_url, "status": "Browserless session ready. Review any ESCRS dialog, then fill the synthetic case."})

            async def controls():
                while True:
                    raw = await ws.receive_text()
                    if len(raw) > 512:
                        raise ValueError("Oversize control")
                    msg = json.loads(raw)
                    async with lock:
                        if msg.get("action") == "fill":
                            if page.url.rstrip("/") != TARGET.rstrip("/"):
                                await ws.send_json({"status": "Return to the ESCRS home form first."})
                                continue
                            await ws.send_json({"status": "Filling and reading back synthetic values…"})
                            await page.add_script_tag(path=str(ROOT / "extensions/escrs-assistant/adapter.js"))
                            try:
                                selected = await page.evaluate("p => CeraiEscrsAdapter.run(p)", synthetic_case())
                                await ws.send_json({"status": "Read-back passed: " + json.dumps(selected)})
                            except Exception:
                                await ws.send_json({"status": "NOT VERIFIED: form fill/read-back failed. Check dialogs and form state."})
                        elif msg.get("action") == "close":
                            return
                        else:
                            raise ValueError("Unknown control")

            await controls()
        finally:
            await browser.close()


@app.websocket("/session")
async def websocket(ws: WebSocket):
    if not authorize(ws) or slot.locked():
        await ws.close(code=1008)
        return
    async with slot:
        await ws.accept()
        try:
            async with asyncio.timeout(TTL):
                await session(ws)
        except WebSocketDisconnect:
            pass
        except Exception:
            with contextlib.suppress(Exception):
                await ws.send_json({"status": "Session ended or Browserless unavailable. No successful transfer confirmed."})
        finally:
            with contextlib.suppress(Exception):
                await ws.close()
