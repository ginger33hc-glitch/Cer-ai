"""Opaque, expiring sessions in the existing encrypted private archive.

Only token hashes identify records. Immutable revocations survive deployments and
are checked on every request; storage failures never grant access.
"""
import hashlib
import json
import re
import secrets
import time

_NAMESPACE = hashlib.sha256(b'CER-AI authentication sessions v1').hexdigest()[:32]
_TOKEN = re.compile(r'^p1\.[A-Za-z0-9_-]{43}$')


class PersistentSessions:
    def __init__(self, archive):
        self.archive = archive

    def _group(self, token):
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        return f'auth-sessions/{digest[:32]}/{digest[32:]}'

    def create(self, username, credential_fingerprint, ttl):
        token = 'p1.' + secrets.token_urlsafe(32)
        record = {'username': username, 'credential_fingerprint': credential_fingerprint,
                  'expires_at': time.time() + ttl}
        self.archive.put_bytes(_NAMESPACE, self._group(token), 'session',
                               json.dumps(record).encode(), media_type='application/json')
        return token

    def read(self, token):
        group = self._group(token)
        if group is None:
            return None
        keys = self.archive.store.list(f'cases/{_NAMESPACE}/{group}/')
        if any(key.rsplit('/', 1)[-1].startswith('revoked-') for key in keys):
            return None
        records = [key for key in keys if key.rsplit('/', 1)[-1].startswith('session-')]
        if len(records) != 1:
            return None
        record = json.loads(self.archive.get_bytes(records[0]))
        if record['expires_at'] <= time.time():
            return None
        return record

    def revoke(self, token):
        group = self._group(token)
        if group is not None:
            self.archive.put_bytes(_NAMESPACE, group, 'revoked', b'{"revoked":true}',
                                   media_type='application/json')
