"""Owner-approved, quota-limited CER-AI demo access.

This module is an operational access boundary. It does not import, wrap, or
modify the clinical engines. Demo requests, password hashes, approvals and
credit-use events are immutable encrypted records in the existing private
archive backend.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from threading import RLock
from time import monotonic
from typing import Any, Optional
from uuid import uuid4

from fastapi import Body, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

import user_access
from demo_notification import DemoEmailNotifier, NotificationResult


DEMO_QUOTA_LIMIT = 10
DEMO_PAGE = Path("static/demo-membership.html")
DEMO_ADMIN_PAGE = Path("static/demo-admin.html")
_LEDGER_CASE_ID = hashlib.sha256(b"CER-AI demo access ledger v1").hexdigest()[:32]
_EVENT_PREFIX = f"cases/{_LEDGER_CASE_ID}/demo-access/"
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_REQUEST_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
_lock = RLock()
_request_starts: dict[str, deque[float]] = defaultdict(deque)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any, *, maximum: int) -> str:
    result = " ".join(str(value or "").strip().split())
    if len(result) > maximum or any(ord(character) < 32 for character in result):
        raise HTTPException(422, "Submitted demo-request information is invalid.")
    return result


class DemoAccessLedger:
    def __init__(self, archive) -> None:
        self.archive = archive

    @property
    def enabled(self) -> bool:
        return self.archive is not None

    def _require_archive(self):
        if self.archive is None:
            raise HTTPException(503, "Demo membership service is temporarily unavailable.")
        return self.archive

    def _events(self) -> list[dict[str, Any]]:
        archive = self._require_archive()
        events: list[dict[str, Any]] = []
        for key in archive.store.list(_EVENT_PREFIX):
            try:
                item = json.loads(archive.get_bytes(key))
            except Exception as exc:
                raise HTTPException(503, "Demo membership records could not be verified.") from exc
            if not isinstance(item, dict) or item.get("ledger") != "CER-AI-DEMO-ACCESS-v1":
                raise HTTPException(503, "Demo membership records failed integrity validation.")
            events.append(item)
        events.sort(key=lambda item: (str(item.get("created_at_utc") or ""), str(item.get("event_id") or "")))
        return events

    def _write(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        archive = self._require_archive()
        event_id = uuid4().hex
        event = {
            "ledger": "CER-AI-DEMO-ACCESS-v1",
            "event_id": event_id,
            "event_type": event_type,
            "created_at_utc": _now(),
            **payload,
        }
        raw = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        archive.put_bytes(
            _LEDGER_CASE_ID,
            f"demo-access/{event_id}",
            event_type.lower().replace("_", "-"),
            raw,
            media_type="application/json",
        )
        return event

    def submit_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        doctor_name = _clean(payload.get("doctor_name"), maximum=160)
        email = _clean(payload.get("email"), maximum=254).lower()
        institution = _clean(payload.get("institution"), maximum=200)
        country = _clean(payload.get("country"), maximum=100)
        phone = _clean(payload.get("phone"), maximum=40)
        specialty = _clean(payload.get("specialty"), maximum=120)
        if not 2 <= len(doctor_name) or not any(character.isalpha() for character in doctor_name):
            raise HTTPException(422, "Doctor name is required.")
        if not _EMAIL_RE.fullmatch(email):
            raise HTTPException(422, "A valid professional email address is required.")
        if not institution:
            raise HTTPException(422, "Institution is required.")
        request_id = uuid4().hex
        self._write("DEMO_REQUESTED", {
            "request_id": request_id,
            "doctor_name": doctor_name,
            "email": email,
            "institution": institution,
            "country": country,
            "phone": phone,
            "specialty": specialty,
            "requested_quota": DEMO_QUOTA_LIMIT,
        })
        return {"request_id": request_id, "status": "PENDING", "quota": DEMO_QUOTA_LIMIT}

    def requests(self) -> list[dict[str, Any]]:
        requests: dict[str, dict[str, Any]] = {}
        for event in self._events():
            request_id = str(event.get("request_id") or "")
            if event.get("event_type") == "DEMO_REQUESTED":
                requests[request_id] = {
                    key: event.get(key)
                    for key in (
                        "request_id", "doctor_name", "email", "institution", "country",
                        "phone", "specialty", "requested_quota", "created_at_utc",
                    )
                }
                requests[request_id]["status"] = "PENDING"
            elif request_id in requests and event.get("event_type") == "DEMO_APPROVED":
                requests[request_id].update({
                    "status": "APPROVED",
                    "username": event.get("username"),
                    "user_id": event.get("user_id"),
                    "approved_at_utc": event.get("created_at_utc"),
                    "quota_limit": event.get("quota_limit"),
                })
            elif request_id in requests and event.get("event_type") == "DEMO_REJECTED":
                requests[request_id].update({
                    "status": "REJECTED",
                    "rejected_at_utc": event.get("created_at_utc"),
                })
            elif request_id in requests and event.get("event_type") == "DEMO_NOTIFICATION":
                requests[request_id].update({
                    "notification_status": event.get("notification_status"),
                    "notification_provider": event.get("notification_provider"),
                    "notification_error_code": event.get("notification_error_code"),
                    "notification_message_id": event.get("notification_message_id"),
                    "notification_attempted_at_utc": event.get("created_at_utc"),
                })
        usage: dict[str, set[str]] = defaultdict(set)
        for event in self._events():
            if event.get("event_type") == "DEMO_CREDIT_USED":
                usage[str(event.get("user_id") or "")].add(str(event.get("usage_id") or ""))
        for item in requests.values():
            if item.get("user_id"):
                used = len(usage[str(item["user_id"])])
                item["credits_used"] = used
                item["credits_remaining"] = max(0, int(item.get("quota_limit") or DEMO_QUOTA_LIMIT) - used)
        return sorted(requests.values(), key=lambda item: str(item.get("created_at_utc") or ""), reverse=True)

    def record_notification(
        self, request_id: str, result: NotificationResult
    ) -> dict[str, Any]:
        if not _REQUEST_ID_RE.fullmatch(str(request_id or "")):
            raise HTTPException(404, "Demo request not found.")
        return self._write("DEMO_NOTIFICATION", {
            "request_id": request_id,
            "notification_status": result.status,
            "notification_provider": result.provider,
            "notification_message_id": result.message_id,
            "notification_error_code": result.error_code,
        })

    def _request(self, request_id: str) -> dict[str, Any]:
        if not _REQUEST_ID_RE.fullmatch(str(request_id or "")):
            raise HTTPException(404, "Demo request not found.")
        match = next((item for item in self.requests() if item["request_id"] == request_id), None)
        if match is None:
            raise HTTPException(404, "Demo request not found.")
        return match

    def approved_accounts(self) -> list[user_access.UserAccount]:
        if not self.enabled:
            return []
        accounts: list[user_access.UserAccount] = []
        for event in self._events():
            if event.get("event_type") != "DEMO_APPROVED":
                continue
            principal = user_access.Principal(
                user_id=str(event["user_id"]),
                username=str(event["username"]),
                display_name=str(event["doctor_name"]),
                role=user_access.ROLE_DOCTOR,
                access_plan="DEMO",
                demo_quota_limit=int(event.get("quota_limit") or DEMO_QUOTA_LIMIT),
                demo_request_id=str(event["request_id"]),
            )
            accounts.append(user_access.UserAccount(
                principal=principal,
                password_hash=str(event["password_hash"]),
                enabled=True,
            ))
        return accounts

    def account_for_username(self, normalized_username: str) -> Optional[user_access.UserAccount]:
        for account in self.approved_accounts():
            if user_access.normalize_username(account.principal.username) == normalized_username:
                return account
        return None

    def account_for_user_id(self, user_id: str) -> Optional[user_access.UserAccount]:
        return next(
            (account for account in self.approved_accounts() if account.principal.user_id == str(user_id)),
            None,
        )

    def approve(self, request_id: str, username: Any, password: Any, owner) -> dict[str, Any]:
        username_display = _clean(username, maximum=64)
        if not _USERNAME_RE.fullmatch(username_display):
            raise HTTPException(422, "Username must be 3-64 characters using letters, numbers, dot, underscore or hyphen.")
        password_text = str(password or "")
        with _lock:
            request = self._request(request_id)
            if request["status"] != "PENDING":
                raise HTTPException(409, "This demo request has already been decided.")
            if user_access.configured_username_exists(username_display):
                raise HTTPException(409, "That username is already in use.")
            try:
                password_hash = user_access.hash_password(password_text)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            user_id = f"demo-{request_id[:24]}"
            event = self._write("DEMO_APPROVED", {
                "request_id": request_id,
                "user_id": user_id,
                "username": username_display,
                "doctor_name": request["doctor_name"],
                "password_hash": password_hash,
                "quota_limit": DEMO_QUOTA_LIMIT,
                "approved_by_user_id": owner.user_id,
            })
        return {
            "status": "APPROVED",
            "request_id": request_id,
            "user_id": user_id,
            "username": username_display,
            "quota_limit": DEMO_QUOTA_LIMIT,
            "approved_at_utc": event["created_at_utc"],
        }

    def reject(self, request_id: str, owner) -> dict[str, Any]:
        with _lock:
            request = self._request(request_id)
            if request["status"] != "PENDING":
                raise HTTPException(409, "This demo request has already been decided.")
            self._write("DEMO_REJECTED", {
                "request_id": request_id,
                "rejected_by_user_id": owner.user_id,
            })
        return {"status": "REJECTED", "request_id": request_id}

    def status_for_user_id(self, user_id: str) -> dict[str, Any]:
        if not self.enabled:
            return {"access_plan": "FULL", "quota_limit": None, "credits_used": None, "credits_remaining": None}
        account = self.account_for_user_id(user_id)
        if account is None or account.principal.access_plan != "DEMO":
            return {"access_plan": "FULL", "quota_limit": None, "credits_used": None, "credits_remaining": None}
        used_ids = {
            str(event.get("usage_id"))
            for event in self._events()
            if event.get("event_type") == "DEMO_CREDIT_USED" and event.get("user_id") == user_id
        }
        limit = int(account.principal.demo_quota_limit or DEMO_QUOTA_LIMIT)
        used = len(used_ids)
        return {
            "access_plan": "DEMO",
            "quota_limit": limit,
            "credits_used": used,
            "credits_remaining": max(0, limit - used),
            "exhausted": used >= limit,
        }

    def assert_credit(self, user_id: str) -> dict[str, Any]:
        status = self.status_for_user_id(user_id)
        if status["access_plan"] == "DEMO" and status["exhausted"]:
            raise HTTPException(
                402,
                "Your 10-patient demo credit has been used. To continue using CER-AI, purchase additional credit.",
            )
        return status

    def consume(self, user_id: str, usage_id: str, module: str) -> dict[str, Any]:
        account = self.account_for_user_id(user_id)
        if account is None or account.principal.access_plan != "DEMO":
            return self.status_for_user_id(user_id)
        usage = _clean(usage_id, maximum=160)
        if not usage:
            raise HTTPException(422, "Demo credit usage identifier is required.")
        with _lock:
            events = self._events()
            if any(
                event.get("event_type") == "DEMO_CREDIT_USED"
                and event.get("user_id") == user_id
                and event.get("usage_id") == usage
                for event in events
            ):
                return self.status_for_user_id(user_id)
            self.assert_credit(user_id)
            self._write("DEMO_CREDIT_USED", {
                "request_id": account.principal.demo_request_id,
                "user_id": user_id,
                "usage_id": usage,
                "module": _clean(module, maximum=40),
            })
        return self.status_for_user_id(user_id)


def _require_owner():
    principal = user_access.require_current_principal()
    if principal.role != user_access.ROLE_OWNER:
        raise HTTPException(403, "Only the CER-AI OWNER role may manage demo requests.")
    return principal


def _admit_public_request(request: Request) -> None:
    address = request.client.host if request.client else "unknown"
    now = monotonic()
    with _lock:
        starts = _request_starts[address]
        cutoff = now - 3600
        while starts and starts[0] <= cutoff:
            starts.popleft()
        if len(starts) >= 5:
            raise HTTPException(429, "Too many demo requests. Please try again later.")
        starts.append(now)


def install(core: Any) -> None:
    if getattr(core, "_cerai_demo_access_installed", False):
        return
    runtime = getattr(core, "_cerai_case_archive_runtime", None)
    ledger = DemoAccessLedger(runtime.archive if runtime and runtime.enabled else None)
    notifier = DemoEmailNotifier.from_environment()
    user_access.set_dynamic_account_lookup(ledger.account_for_username)
    core._cerai_demo_access = ledger
    core._cerai_demo_notifier = notifier
    core._cerai_assert_demo_credit = ledger.assert_credit
    core._cerai_consume_demo_credit = ledger.consume

    @core.app.get("/demo-membership", include_in_schema=False)
    def demo_membership_page():
        return FileResponse(DEMO_PAGE, media_type="text/html", headers={"Cache-Control": "no-store"})

    @core.app.post("/demo-access/request", include_in_schema=False)
    def request_demo(request: Request, payload: dict[str, Any] = Body(...)):
        _admit_public_request(request)
        if str(payload.get("website") or "").strip():
            return JSONResponse({"status": "PENDING"}, status_code=202)
        submitted = ledger.submit_request(payload)
        notification = notifier.send(ledger._request(submitted["request_id"]))
        ledger.record_notification(submitted["request_id"], notification)
        submitted["notification_status"] = notification.status
        return JSONResponse(submitted, status_code=201, headers={"Cache-Control": "no-store"})

    @core.app.get("/demo-admin", include_in_schema=False)
    def demo_admin_page():
        _require_owner()
        return FileResponse(DEMO_ADMIN_PAGE, media_type="text/html", headers={"Cache-Control": "no-store"})

    @core.app.get("/demo-access/admin/requests", include_in_schema=False)
    def demo_requests():
        _require_owner()
        return {"requests": ledger.requests()}

    @core.app.post("/demo-access/admin/requests/{request_id}/approve", include_in_schema=False)
    def approve_demo(request_id: str, payload: dict[str, Any] = Body(...)):
        owner = _require_owner()
        return ledger.approve(request_id, payload.get("username"), payload.get("password"), owner)

    @core.app.post("/demo-access/admin/requests/{request_id}/reject", include_in_schema=False)
    def reject_demo(request_id: str):
        return ledger.reject(request_id, _require_owner())

    @core.app.get("/demo-access/status", include_in_schema=False)
    def demo_status():
        principal = user_access.require_current_principal()
        return ledger.status_for_user_id(principal.user_id)

    core._cerai_demo_access_installed = True


def _reset_rate_limit_for_tests() -> None:
    with _lock:
        _request_starts.clear()
