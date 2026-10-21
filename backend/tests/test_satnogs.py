import asyncio
import time

import pytest

from services import satnogs
from utils.config import RESILIENCE_CONFIG, SATNOGS_CONFIG


def fetch(endpoint: str = "observations"):
    return satnogs.fetch_with_cache(
        endpoint=endpoint,
        params={"sat_id": "ZDPY-4221-9426-0630-5344"},
        ttl=300,
        source="NETWORK",
        url_builder=lambda p: f"https://network.test/observations/?sat_id={p['sat_id']}",
    )


def fail_until_breaker_opens():
    for _ in range(RESILIENCE_CONFIG["CIRCUIT_FAILURE_THRESHOLD"]):
        with pytest.raises(Exception):
            asyncio.run(fetch())


def test_breaker_opens_after_threshold_failures_and_stops_calling_satnogs(fake_satnogs):
    fake_satnogs.status = 503
    fail_until_breaker_opens()
    calls_before = len(fake_satnogs.requests)

    with pytest.raises(Exception, match="Circuit breaker open"):
        asyncio.run(fetch())

    assert satnogs.circuit_breakers["NETWORK"].is_open()
    assert len(fake_satnogs.requests) == calls_before


def test_open_breaker_lets_a_trial_request_through_after_recovery_timeout(fake_satnogs, monkeypatch):
    fake_satnogs.status = 503
    fail_until_breaker_opens()
    assert satnogs.circuit_breakers["NETWORK"].is_open()

    later = time.time() + RESILIENCE_CONFIG["CIRCUIT_RECOVERY_TIMEOUT"] + 1
    monkeypatch.setattr(satnogs.time, "time", lambda: later)
    fake_satnogs.status = 200
    fake_satnogs.body = [{"id": 1}]

    data, source, _ = asyncio.run(fetch())

    assert (data, source) == ([{"id": 1}], "live")
    assert not satnogs.circuit_breakers["NETWORK"].is_open()


def test_retry_backoff_does_not_block_the_event_loop(fake_satnogs, monkeypatch):
    fake_satnogs.status = 503
    monkeypatch.setitem(RESILIENCE_CONFIG, "RETRY_MAX_ATTEMPTS", 2)
    monkeypatch.setitem(RESILIENCE_CONFIG, "RETRY_BACKOFF_FACTOR", 0.3)
    ticks = []

    async def ticker():
        for _ in range(5):
            ticks.append(time.monotonic())
            await asyncio.sleep(0.05)

    async def scenario():
        results = await asyncio.gather(fetch(), ticker(), return_exceptions=True)
        return results

    started = time.monotonic()
    asyncio.run(scenario())

    ticks_during_backoff = [t for t in ticks if t - started < 0.25]
    assert len(ticks_during_backoff) >= 3


def test_requests_carry_no_authorization_header_without_a_token(fake_satnogs, monkeypatch):
    monkeypatch.setitem(SATNOGS_CONFIG, "NETWORK_TOKEN", None)

    asyncio.run(fetch())

    assert "authorization" not in fake_satnogs.requests[0].headers


def test_requests_send_the_token_when_configured(fake_satnogs, monkeypatch):
    monkeypatch.setitem(SATNOGS_CONFIG, "NETWORK_TOKEN", "abc123")

    asyncio.run(fetch())

    assert fake_satnogs.requests[0].headers["authorization"] == "Token abc123"
