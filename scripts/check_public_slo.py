"""PHI-free public production availability and latency check."""
from __future__ import annotations

import json
import statistics
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE_URL = "https://cer-ai.com"
SAMPLES = 5
P95_LIMIT_SECONDS = 10.0


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(path: str, *, follow: bool = True) -> dict[str, object]:
    opener = build_opener() if follow else build_opener(NoRedirect)
    started = time.monotonic()
    try:
        response = opener.open(Request(BASE_URL + path, headers={"User-Agent": "CER-AI-SLO/1"}), timeout=20)
        status = response.status
        location = response.headers.get("Location")
        response.read(256)
    except HTTPError as exc:
        status = exc.code
        location = exc.headers.get("Location")
    return {"path": path, "status": status, "location": location, "seconds": round(time.monotonic() - started, 3)}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
    return ordered[index]


def main() -> None:
    samples = [request("/") for _ in range(SAMPLES)]
    health = request("/health")
    app = request("/app", follow=False)
    durations = [float(item["seconds"]) for item in samples]
    summary = {
        "homepage_statuses": [item["status"] for item in samples],
        "homepage_p50_seconds": round(statistics.median(durations), 3),
        "homepage_p95_seconds": percentile(durations, 0.95),
        "health": health,
        "app_boundary": app,
    }
    print(json.dumps(summary, sort_keys=True))
    assert all(item["status"] == 200 for item in samples)
    assert health["status"] == 200
    assert app["status"] in (302, 303, 307, 308)
    assert str(app.get("location") or "").startswith("/auth/login-page")
    assert summary["homepage_p95_seconds"] <= P95_LIMIT_SECONDS


if __name__ == "__main__":
    main()
