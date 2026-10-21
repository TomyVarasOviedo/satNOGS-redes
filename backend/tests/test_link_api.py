import pytest
from fastapi.testclient import TestClient

from main import app
from tests.tle_fixtures import LUSAT_OBSERVATION, LUSAT_TRANSMITTERS

client = TestClient(app)

LUSAT_TLE_RESPONSE = [{"tle0": "0 LUSAT", "tle1": LUSAT_OBSERVATION["tle1"], "tle2": LUSAT_OBSERVATION["tle2"]}]
LUSAT_PASS_QUERY = {
    "sat_id": "ZDPY-4221-9426-0630-5344",
    "lat": LUSAT_OBSERVATION["station_lat"],
    "lng": LUSAT_OBSERVATION["station_lng"],
    "alt": LUSAT_OBSERVATION["station_alt"],
    "horizon_deg": 0,
    "start": "2026-10-17T01:45:00Z",
}


@pytest.fixture
def lusat(fake_satnogs):
    fake_satnogs.routes = {"/tle/": LUSAT_TLE_RESPONSE, "/transmitters/": LUSAT_TRANSMITTERS}
    return fake_satnogs


def test_linkbudget_calculator_with_explicit_distance():
    response = client.get(
        "/linkbudget",
        params={"freq_hz": 437e6, "distance_km": 1000, "eirp_dbw": 0, "gain_dbi": 12, "noise_k": 500, "baud": 1200, "mode": "BPSK"},
    )

    assert response.status_code == 200
    assert response.json()["margin_db"] == pytest.approx(27.97, abs=0.01)


def test_linkbudget_derives_distance_from_elevation_and_altitude():
    response = client.get("/linkbudget", params={"freq_hz": 437e6, "elevation_deg": 90, "altitude_km": 800})

    assert response.json()["distance_km"] == pytest.approx(800)


def test_linkbudget_needs_a_distance_or_a_geometry():
    assert client.get("/linkbudget", params={"freq_hz": 437e6}).status_code == 422


def test_doppler_for_the_next_pass_uses_the_satellite_downlink(lusat):
    response = client.get("/predictions/doppler", params={**LUSAT_PASS_QUERY, "days": 1})

    body = response.json()
    assert response.status_code == 200
    assert body["transmitter"]["description"] == "BPSK 1k2 Transceiver"
    assert body["f0_hz"] == 437_150_000
    assert body["pass"]["aos"] == "2026-10-17T02:14:52Z"
    assert 8_000 < body["max_shift_hz"] < 11_000


def test_doppler_frequency_override_skips_the_transmitter(lusat):
    response = client.get("/predictions/doppler", params={**LUSAT_PASS_QUERY, "freq_hz": 145.8e6})

    assert response.json()["f0_hz"] == 145.8e6


def test_passes_carry_the_link_margin_at_tca_and_at_the_mask(lusat):
    response = client.get("/predictions/passes", params={**LUSAT_PASS_QUERY, "days": 1 / 24})

    link = response.json()["passes"][0]["link"]
    assert link["mode"] == "BPSK"
    assert link["margin_at_tca_db"] > link["margin_at_aos_db"]


def test_passes_still_work_when_transmitters_are_unavailable(fake_satnogs):
    fake_satnogs.routes = {"/tle/": LUSAT_TLE_RESPONSE, "/transmitters/": []}

    response = client.get("/predictions/passes", params={**LUSAT_PASS_QUERY, "days": 1 / 24})

    assert response.status_code == 200
    assert response.json()["passes"][0]["link"] is None
