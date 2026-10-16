import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from experiments.escrs_cloud import server


def test_cross_origin_and_missing_cookie_are_rejected():
    for cookie, origin in [(None, "http://testserver"), (server.TOKEN, "https://other.example")]:
        ws = SimpleNamespace(cookies={"cloud_demo": cookie},
                             headers={"host": "testserver", "origin": origin})
        assert not server.authorize(ws)


def test_session_cannot_start_without_viewer_cookie():
    with TestClient(server.app) as client:
        with pytest.raises(Exception) as caught:
            with client.websocket_connect("/session", headers={"origin": "http://testserver"}):
                pass
        assert getattr(caught.value, "code", None) == 1008


def test_viewer_only_exposes_fixed_synthetic_case(monkeypatch):
    called = AsyncMock()
    monkeypatch.setattr(server, "session", called)
    with TestClient(server.app) as client:
        response = client.get("/")
        assert response.headers["cache-control"] == "no-store"
        assert "HttpOnly" in response.headers["set-cookie"]
        with client.websocket_connect("/session", headers={"origin": "http://testserver"}):
            pass
    called.assert_awaited_once()
    case = server.synthetic_case()
    assert case["eyes"]["OD"]["toric"] is True
    assert case["eyes"]["OS"]["toric"] is False


def test_browser_closes_when_navigation_fails(monkeypatch):
    monkeypatch.setenv("BROWSERLESS_TOKEN", "synthetic-test-token")
    page = SimpleNamespace(goto=AsyncMock(side_effect=RuntimeError("navigation failed")))
    context = SimpleNamespace(new_page=AsyncMock(return_value=page))
    browser = SimpleNamespace(new_context=AsyncMock(return_value=context), close=AsyncMock())
    pw = SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=AsyncMock(return_value=browser)))

    class Manager:
        async def __aenter__(self):
            return pw

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(server, "async_playwright", Manager)
    with pytest.raises(RuntimeError, match="navigation failed"):
        asyncio.run(server.session(AsyncMock()))
    browser.close.assert_awaited_once()
