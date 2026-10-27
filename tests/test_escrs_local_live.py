"""Opt-in synthetic ESCRS integration: real Chromium and >2 minute retention."""
import os
from time import sleep
import pytest
from iol_module import escrs_local as local
from iol_module.escrs_cloud import CloudTransfer
from test_escrs_cloud import case


@pytest.mark.skipif(os.environ.get('CERAI_ESCRS_LIVE_TEST') != '1', reason='Explicit synthetic live check only')
def test_real_escrs_transfer_and_retention():
    payload=case()
    payload.update(initials='TEST',surgeon='CERAI SYNTHETIC TEST',provider='local',consent_version='ESCRS-CLOUD-2026-10-17-V2')
    result=local.create_local_transfer(CloudTransfer.model_validate(payload),'synthetic-test')
    record=local._owned(result['escrs_url'].rsplit('/',1)[1],'synthetic-test')
    try:
        assert result['verified'] and result['viewer_limit_seconds']==900
        assert len(local._request(record,{'kind':'frame'})) > 1000
        sleep(125)
        assert local._owned(record.view_id,'synthetic-test') is record
        assert len(local._request(record,{'kind':'frame'})) > 1000
        assert len(local._request(record,{'kind':'pdf'})) > 1000
    finally:
        record.stop.set()
    for _ in range(100):
        if record.view_id not in local._sessions:
            break
        sleep(.1)
    assert record.view_id not in local._sessions
