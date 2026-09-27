import json
from pathlib import Path

import pytest

import case_archive
import demo_access
from demo_notification import NotificationResult
import user_access


def _owner_registry():
    payload = [{
        "user_id": "owner-1",
        "username": "owner",
        "display_name": "Owner",
        "role": "OWNER",
        "password_hash": user_access.hash_password(
            "long-owner-password", salt=bytes(range(16))
        ),
        "enabled": True,
    }]
    return user_access.parse_registry(json.dumps(payload))


@pytest.fixture
def ledger():
    archive = case_archive.EncryptedArchive(
        case_archive.MemoryObjectStore(), bytes(range(32))
    )
    result = demo_access.DemoAccessLedger(archive)
    user_access._configure_for_tests(_owner_registry())
    user_access.set_dynamic_account_lookup(result.account_for_username)
    yield result
    user_access._reset_for_tests()


def _request(ledger):
    return ledger.submit_request({
        "doctor_name": "Dr. Demo Surgeon",
        "institution": "Demo Eye Clinic",
        "email": "doctor@example.org",
        "phone": "+90 555 000 00 00",
        "country": "Türkiye",
        "specialty": "Ophthalmology",
    })


def test_owner_approval_creates_password_account_without_storing_plaintext(ledger):
    request = _request(ledger)
    owner = user_access.Principal("owner-1", "owner", "Owner", "OWNER")
    approved = ledger.approve(
        request["request_id"], "demo.surgeon", "strong-demo-password", owner
    )

    assert approved["quota_limit"] == 10
    principal = user_access.authenticate_credentials(
        "demo.surgeon", "strong-demo-password"
    )
    assert principal.access_plan == "DEMO"
    assert principal.demo_quota_limit == 10
    assert principal.role == "DOCTOR"

    decrypted = b"\n".join(
        ledger.archive.get_bytes(key)
        for key in ledger.archive.store.list(demo_access._EVENT_PREFIX)
    )
    assert b"strong-demo-password" not in decrypted
    assert b"scrypt$" in decrypted


def test_demo_account_is_limited_to_ten_unique_patient_uses(ledger):
    request = _request(ledger)
    owner = user_access.Principal("owner-1", "owner", "Owner", "OWNER")
    approved = ledger.approve(
        request["request_id"], "demo-doctor", "strong-demo-password", owner
    )
    user_id = approved["user_id"]

    for index in range(10):
        status = ledger.consume(user_id, f"patient-{index}", "REFRACTIVE")
    assert status["credits_used"] == 10
    assert status["credits_remaining"] == 0
    assert status["exhausted"] is True

    # A transport retry for the same patient is idempotent and costs no extra credit.
    assert ledger.consume(user_id, "patient-9", "REFRACTIVE")["credits_used"] == 10
    with pytest.raises(Exception) as exc:
        ledger.assert_credit(user_id)
    assert getattr(exc.value, "status_code", None) == 402


def test_request_can_be_rejected_and_cannot_then_be_approved(ledger):
    request = _request(ledger)
    owner = user_access.Principal("owner-1", "owner", "Owner", "OWNER")
    ledger.reject(request["request_id"], owner)
    assert ledger.requests()[0]["status"] == "REJECTED"
    with pytest.raises(Exception) as exc:
        ledger.approve(
            request["request_id"], "late-doctor", "strong-demo-password", owner
        )
    assert getattr(exc.value, "status_code", None) == 409


def test_notification_delivery_state_is_retained_with_the_owner_request(ledger):
    request = _request(ledger)
    ledger.record_notification(
        request["request_id"],
        NotificationResult("SENT", "FORMSUBMIT", message_id=request["request_id"]),
    )
    record = ledger.requests()[0]
    assert record["notification_status"] == "SENT"
    assert record["notification_provider"] == "FORMSUBMIT"
    assert record["notification_message_id"] == request["request_id"]


def test_public_and_login_pages_expose_bilingual_demo_request_entry():
    root = Path(__file__).resolve().parents[1]
    homepage = (root / "static" / "public-home.html").read_text(encoding="utf-8")
    login = (root / "static" / "login.html").read_text(encoding="utf-8")
    translations = (root / "static" / "public-i18n.js").read_text(encoding="utf-8")
    phrase = "Not a member yet? Click here to request a free 10-patient demo membership."
    assert phrase in homepage
    assert phrase in login
    assert 'href="/demo-membership"' in homepage
    assert 'href="/demo-membership"' in login
    assert "Henüz üyeliğiniz yoksa 10 hastalık ücretsiz demo üyeliği için tıklayınız." in translations
