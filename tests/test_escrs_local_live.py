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
    payload.update(initials='TEST',surgeon='CER-AI SYNTHETIC TEST',provider='local',consent_version='ESCRS-CLOUD-2026-10-17-V2')
    result=local.create_local_transfer(CloudTransfer.model_validate(payload),'synthetic-test')
    record=local._owned(result['escrs_url'].rsplit('/',1)[1],'synthetic-test')
    try:
        assert result['verified'] and result['viewer_limit_seconds']==900
        assert len(local._request(record,{'kind':'frame'})) > 1000
        fields=local._request(record,{'kind':'fields'})
        surgeon=next(item for item in fields if item['value']=='CER-AI SYNTHETIC TEST')
        local._request(record,{'kind':'edit','field':surgeon['id'],'text':'CER-AI UI TEST'})
        assert any(item['value']=='CER-AI UI TEST' for item in local._request(record,{'kind':'fields'}))
        local._request(record,{'kind':'edit','field':surgeon['id'],'text':'CER-AI SYNTHETIC TEST'})
        local._request(record,{'kind':'scroll','delta':400})
        verify_mobile_viewer(record)
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


def verify_mobile_viewer(record):
    from types import SimpleNamespace
    from unittest.mock import patch
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.testclient import TestClient
    from playwright.sync_api import sync_playwright
    core=SimpleNamespace(app=FastAPI())
    local.install(core)
    core.app.mount('/static',StaticFiles(directory='static'),name='static')
    with patch('user_access.require_current_principal',return_value=SimpleNamespace(user_id='synthetic-test')), TestClient(core.app) as client, sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=local.executable(),args=['--no-sandbox'])
        try:
            page=browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
            def route(req):
                from urllib.parse import urlsplit
                path=urlsplit(req.request.url).path
                response=client.request(req.request.method,path,content=req.request.post_data,
                    headers={'content-type':req.request.headers.get('content-type','')})
                req.fulfill(status=response.status_code,headers=dict(response.headers),body=response.content)
            page.route('**/*',route)
            page.goto('http://testserver/iol/escrs-local/'+record.view_id)
            page.locator('.field').first.wait_for()
            assert page.locator('#keyboard').count()==0
            assert page.locator('#send').count()==0
            values=page.locator('.field').evaluate_all('(items)=>items.map(e=>e.value)')
            # After scrolling, edit an actually visible field and verify native input delivery.
            index=next(i for i,v in enumerate(values) if v and len(v)<100)
            field=page.locator('.field').nth(index)
            original=field.input_value()
            field.fill(original)
            field.blur()
            page.wait_for_timeout(1000)
            assert not page.locator('#viewport').is_hidden()
            assert page.locator('#status').inner_text()==''
        finally:
            browser.close()
