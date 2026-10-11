import json
import pytest
from fastapi import HTTPException
from case_archive import EncryptedArchive, MemoryObjectStore
import user_access
import persistent_sessions


@pytest.fixture
def session_setup():
    registry = user_access.parse_registry(json.dumps([{
        'user_id': 'owner-1', 'username': 'owner', 'display_name': 'Owner', 'role': 'OWNER',
        'password_hash': user_access.hash_password('long-owner-password'), 'enabled': True}]))
    archive = EncryptedArchive(MemoryObjectStore(), bytes(range(32)))
    user_access._configure_for_tests(registry)
    user_access.set_session_archive(archive)
    yield archive, registry['owner']
    user_access._reset_for_tests()


def test_restart_preserves_session_and_logout_revokes_across_instances(session_setup):
    archive, account = session_setup
    token = user_access.create_session(account.principal)
    assert all(token not in key for key in archive.store.objects)
    assert all(token.encode() not in obj.data for obj in archive.store.objects.values())
    user_access._sessions.clear()
    user_access.set_session_archive(archive)
    assert user_access.principal_for_token(token) == account.principal
    user_access.remove_session(token)
    user_access.set_session_archive(archive)
    assert user_access.principal_for_token(token) is None


def test_expired_and_forged_sessions_rejected(session_setup, monkeypatch):
    _, account = session_setup
    token = user_access.create_session(account.principal)
    assert user_access.principal_for_token(token + 'x') is None
    now = persistent_sessions.time.time()
    monkeypatch.setattr(persistent_sessions.time, 'time', lambda: now + user_access.SESSION_TTL_SECONDS + 1)
    assert user_access.principal_for_token(token) is None


def test_changed_credentials_and_disabled_accounts_revoke_session(session_setup):
    _, account = session_setup
    token = user_access.create_session(account.principal)
    user_access._users_by_username['owner'] = user_access.UserAccount(account.principal, account.password_hash, False)
    assert user_access.principal_for_token(token) is None
    user_access._users_by_username['owner'] = user_access.UserAccount(account.principal, user_access.hash_password('new-owner-password'))
    assert user_access.principal_for_token(token) is None


def test_storage_outage_fails_closed(session_setup, monkeypatch):
    archive, account = session_setup
    token = user_access.create_session(account.principal)
    def fail(*args):
        raise OSError('storage unavailable')
    monkeypatch.setattr(archive.store, 'list', fail)
    with pytest.raises(HTTPException) as error:
        user_access.principal_for_token(token)
    assert error.value.status_code == 503
