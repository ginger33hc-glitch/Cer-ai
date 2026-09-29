"""Privacy-minimised owner notification for new CER-AI demo requests."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


FORMSUBMIT_AJAX_ENDPOINT = "https://formsubmit.co/ajax"
NTFY_ENDPOINT = "https://ntfy.sh"
OWNER_PANEL_URL = "https://cer-ai.com/demo-admin"


@dataclass(frozen=True)
class NotificationResult:
    status: str
    provider: str
    message_id: Optional[str] = None
    error_code: Optional[str] = None

    def public(self) -> dict[str, Optional[str]]:
        return {
            "status": self.status,
            "provider": self.provider,
            "message_id": self.message_id,
            "error_code": self.error_code,
        }


class DemoEmailNotifier:
    """Notify the owner without sharing applicant personal data.

    FormSubmit requires no API credential. The recipient must confirm its
    one-time activation message before subsequent notifications are delivered.
    """

    def __init__(
        self,
        *,
        recipient: str,
        transport: Optional[Callable[[Request, float], dict[str, Any]]] = None,
    ) -> None:
        self.recipient = str(recipient or "").strip()
        self.transport = transport or self._urlopen_transport

    @classmethod
    def from_environment(cls) -> "DemoEmailNotifier":
        return cls(recipient=os.getenv("CERAI_DEMO_NOTIFICATION_RECIPIENT", ""))

    @property
    def configured(self) -> bool:
        return bool(self.recipient)

    @property
    def provider_name(self) -> str:
        return "FORMSUBMIT"

    @staticmethod
    def _urlopen_transport(request: Request, timeout: float) -> dict[str, Any]:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS endpoint
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _payload(request_id: str) -> bytes:
        # Deliberately exclude the doctor's name, email, phone and institution.
        return urlencode({
            "_subject": "CER-AI: Yeni demo üyelik talebi",
            "_template": "table",
            "message": "Bir hekim için yeni demo hesabı talebi owner onayı bekliyor.",
            "owner_panel": OWNER_PANEL_URL,
            "request_reference": request_id,
            "privacy": "Başvuru sahibinin kişisel bilgileri bu e-postaya eklenmemiştir.",
        }).encode("utf-8")

    def send(self, item: dict[str, Any]) -> NotificationResult:
        if not self.configured:
            return NotificationResult(
                "NOT_CONFIGURED", "FORMSUBMIT", error_code="MISSING_CONFIGURATION"
            )
        request_id = str(item.get("request_id") or "").strip()
        if not request_id:
            return NotificationResult("FAILED", "FORMSUBMIT", error_code="MISSING_REQUEST_ID")
        request = Request(
            f"{FORMSUBMIT_AJAX_ENDPOINT}/{quote(self.recipient, safe='@')}",
            data=self._payload(request_id),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "CER-AI/2.0",
            },
        )
        try:
            response = self.transport(request, 20.0)
            if response.get("success") not in (True, "true", "True"):
                return NotificationResult("FAILED", "FORMSUBMIT", error_code="PROVIDER_REJECTED")
            return NotificationResult("SENT", "FORMSUBMIT", message_id=request_id)
        except HTTPError as exc:
            return NotificationResult("FAILED", "FORMSUBMIT", error_code=f"HTTP_{exc.code}")
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return NotificationResult("FAILED", "FORMSUBMIT", error_code="TRANSPORT_ERROR")


class DemoPushNotifier:
    """Send a generic owner push without applicant data to a private random topic.

    ntfy.sh topics are publicly readable by anyone who knows the topic name.
    Keep the topic secret; the message contains only a link to the authenticated
    owner panel and a request reference.
    """

    def __init__(
        self,
        *,
        topic: str,
        transport: Optional[Callable[[Request, float], dict[str, Any]]] = None,
    ) -> None:
        self.topic = str(topic or "").strip()
        self.transport = transport or DemoEmailNotifier._urlopen_transport

    @classmethod
    def from_environment(cls) -> "DemoPushNotifier":
        return cls(topic=os.getenv("CERAI_DEMO_NTFY_TOPIC", ""))

    @property
    def configured(self) -> bool:
        # A high entropy, opaque topic prevents accidental discovery. Never use
        # a doctor or owner name, email, or a predictable site name here.
        return len(self.topic) >= 32 and self.topic.isascii() and self.topic.isalnum()

    @property
    def provider_name(self) -> str:
        return "NTFY"

    @property
    def subscription_url(self) -> str:
        return f"ntfy://ntfy.sh/{self.topic}"

    def send(self, item: dict[str, Any]) -> NotificationResult:
        if not self.configured:
            return NotificationResult("NOT_CONFIGURED", "NTFY", error_code="MISSING_CONFIGURATION")
        request_id = str(item.get("request_id") or "").strip()
        if not request_id:
            return NotificationResult("FAILED", "NTFY", error_code="MISSING_REQUEST_ID")
        request = Request(
            f"{NTFY_ENDPOINT}/{self.topic}",
            data=f"New CER-AI demo request. Reference: {request_id}. Review in owner panel.".encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain; charset=UTF-8",
                "Title": "CER-AI demo request",
                "Click": OWNER_PANEL_URL,
                "Priority": "high",
                "User-Agent": "CER-AI/2.0",
            },
        )
        try:
            response = self.transport(request, 6.0)
            if not response.get("id") or response.get("event") != "message":
                return NotificationResult("FAILED", "NTFY", error_code="PROVIDER_REJECTED")
            return NotificationResult("SENT", "NTFY", message_id=str(response["id"]))
        except HTTPError as exc:
            return NotificationResult("FAILED", "NTFY", error_code=f"HTTP_{exc.code}")
        except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return NotificationResult("FAILED", "NTFY", error_code="TRANSPORT_ERROR")


def configured_demo_notifier() -> DemoPushNotifier | DemoEmailNotifier:
    """Use the owner's push channel when configured; retain legacy email otherwise."""
    push = DemoPushNotifier.from_environment()
    return push if push.topic else DemoEmailNotifier.from_environment()
