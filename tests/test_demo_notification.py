import json
from urllib.error import URLError
from urllib.parse import parse_qs

import demo_notification


def _request_record():
    return {
        "request_id": "a" * 32,
        "doctor_name": "Dr. Demo Surgeon",
        "institution": "Demo Eye Clinic",
        "email": "doctor@example.org",
        "phone": "+90 555 000 00 00",
        "country": "Türkiye",
        "specialty": "Ophthalmology",
        "created_at_utc": "2026-09-27T19:00:00+00:00",
    }


def test_formsubmit_notification_contains_only_reference_and_owner_panel():
    captured = {}

    def transport(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.header_items())
        captured["payload"] = parse_qs(request.data.decode("utf-8"))
        return {"success": "true"}

    notifier = demo_notification.DemoEmailNotifier(
        recipient="owner@example.org",
        transport=transport,
    )
    result = notifier.send(_request_record())

    assert result.status == "SENT"
    assert result.provider == "FORMSUBMIT"
    assert result.message_id == "a" * 32
    assert captured["url"] == "https://formsubmit.co/ajax/owner@example.org"
    assert captured["timeout"] == 20.0
    assert captured["headers"]["Content-type"].startswith("application/x-www-form-urlencoded")
    assert captured["payload"]["owner_panel"] == ["https://cer-ai.com/demo-admin"]
    assert captured["payload"]["request_reference"] == ["a" * 32]
    encoded_payload = str(captured["payload"])
    for personal_value in (
        "Dr. Demo Surgeon",
        "Demo Eye Clinic",
        "doctor@example.org",
        "+90 555 000 00 00",
        "Ophthalmology",
    ):
        assert personal_value not in encoded_payload


def test_notification_configuration_and_transport_failures_are_non_secret_statuses():
    missing = demo_notification.DemoEmailNotifier(recipient="")
    assert missing.send(_request_record()).public() == {
        "status": "NOT_CONFIGURED",
        "provider": "FORMSUBMIT",
        "message_id": None,
        "error_code": "MISSING_CONFIGURATION",
    }

    def failed_transport(_request, _timeout):
        raise URLError("network detail that must not be persisted")

    failed = demo_notification.DemoEmailNotifier(
        recipient="owner@example.org",
        transport=failed_transport,
    ).send(_request_record())
    assert failed.status == "FAILED"
    assert failed.error_code == "TRANSPORT_ERROR"
    assert "network detail" not in json.dumps(failed.public())

    rejected = demo_notification.DemoEmailNotifier(
        recipient="owner@example.org",
        transport=lambda _request, _timeout: {"success": False, "message": "private detail"},
    ).send(_request_record())
    assert rejected.status == "FAILED"
    assert rejected.error_code == "PROVIDER_REJECTED"
    assert "private detail" not in json.dumps(rejected.public())


def test_push_notification_contains_no_applicant_information():
    captured = {}

    def transport(request, timeout):
        captured.update(url=request.full_url, timeout=timeout, body=request.data.decode(), headers=dict(request.header_items()))
        return {"event": "message", "id": "push-123"}

    result = demo_notification.DemoPushNotifier(topic="a" * 40, transport=transport).send(_request_record())
    assert result.status == "SENT"
    assert result.provider == "NTFY"
    assert result.message_id == "push-123"
    assert captured["url"] == "https://ntfy.sh/" + "a" * 40
    assert captured["timeout"] == 6.0
    assert captured["headers"]["Click"] == "https://cer-ai.com/demo-admin"
    assert "a" * 32 in captured["body"]
    for personal_value in ("Dr. Demo Surgeon", "Demo Eye Clinic", "doctor@example.org", "+90 555 000 00 00"):
        assert personal_value not in str(captured)


def test_push_failure_and_bad_topic_fail_closed(monkeypatch):
    monkeypatch.setenv("CERAI_DEMO_NTFY_TOPIC", "short")
    assert demo_notification.configured_demo_notifier().send(_request_record()).status == "NOT_CONFIGURED"
    failed = demo_notification.DemoPushNotifier(topic="b" * 40, transport=lambda _request, _timeout: {"event": "error"}).send(_request_record())
    assert failed.error_code == "PROVIDER_REJECTED"
    monkeypatch.delenv("CERAI_DEMO_NTFY_TOPIC")
    monkeypatch.setenv("CERAI_DEMO_NOTIFICATION_RECIPIENT", "owner@example.org")
    assert isinstance(demo_notification.configured_demo_notifier(), demo_notification.DemoEmailNotifier)
