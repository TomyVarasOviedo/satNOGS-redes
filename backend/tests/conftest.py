import httpx
import pytest

from services import satnogs
from utils.cache import cache_manager
from utils.config import RESILIENCE_CONFIG


class FakeSatnogs:
    """Stands in for the SatNOGS APIs: records every request and answers with `status`/`body`."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.status = 200
        self.body = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body)


@pytest.fixture
def fake_satnogs(monkeypatch, tmp_path):
    fake = FakeSatnogs()
    real_client = httpx.AsyncClient

    monkeypatch.setattr(
        satnogs.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(fake.handler), **kwargs),
    )
    monkeypatch.setattr(cache_manager, "cache_dir", tmp_path)
    monkeypatch.setitem(RESILIENCE_CONFIG, "RETRY_MAX_ATTEMPTS", 1)
    monkeypatch.setitem(RESILIENCE_CONFIG, "RETRY_BACKOFF_FACTOR", 0)
    for breaker in satnogs.circuit_breakers.values():
        breaker.on_success()
    return fake
