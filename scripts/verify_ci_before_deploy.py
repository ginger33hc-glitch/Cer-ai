"""Fail-closed Railway pre-deploy verification of this exact commit's CI."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from urllib.request import Request, urlopen

REPOSITORY = "ginger33hc-glitch/Cer-ai"
REQUIRED_WORKFLOWS = (
    ".github/workflows/canonical-runtime.yml",
    ".github/workflows/deep-import-isolation.yml",
)


def verdict(runs: list[dict], sha: str) -> tuple[str, str]:
    """Use the newest push run per required workflow, never an older success."""
    selected = {}
    for run in runs:
        path = run.get("path")
        if (path in REQUIRED_WORKFLOWS and run.get("head_sha") == sha
                and run.get("event") == "push" and run.get("head_branch") == "main"):
            previous = selected.get(path)
            if previous is None or int(run["id"]) > int(previous["id"]):
                selected[path] = run
    pending = []
    for path in REQUIRED_WORKFLOWS:
        run = selected.get(path)
        if run is None or run.get("status") != "completed":
            pending.append(path)
        elif run.get("conclusion") != "success":
            return "failed", f"{path}: {run.get('conclusion')}"
    if pending:
        return "pending", ", ".join(pending)
    return "success", "Full regression, dependency audit and file isolation passed."


def main() -> int:
    sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA", "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        print("Deployment blocked: a full source commit SHA is required.", file=sys.stderr)
        return 1
    url = f"https://api.github.com/repos/{REPOSITORY}/actions/runs?head_sha={sha}&event=push&per_page=100"
    deadline = time.monotonic() + 600
    while True:
        try:
            request = Request(url, headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "CER-AI-production-CI-gate",
            })
            with urlopen(request, timeout=20) as response:
                runs = json.load(response)["workflow_runs"]
            state, detail = verdict(runs, sha)
        except Exception as exc:
            print(f"Deployment blocked: CI could not be verified ({type(exc).__name__}).", file=sys.stderr)
            return 1
        print(f"CI gate {sha[:12]}: {state}: {detail}", flush=True)
        if state == "success":
            return 0
        if state == "failed" or time.monotonic() >= deadline:
            return 1
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
