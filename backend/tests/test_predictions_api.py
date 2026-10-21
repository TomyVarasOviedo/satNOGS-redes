from fastapi.testclient import TestClient

from main import app
from tests.tle_fixtures import ISS

client = TestClient(app)

ISS_TLE_RESPONSE = [{"tle0": "0 ISS (ZARYA)", "tle1": ISS[0], "tle2": ISS[1], "sat_id": "XSKZ-5603-1870-9019-3066"}]


def test_classify_reads_the_current_tle_from_satnogs_db(fake_satnogs):
    fake_satnogs.body = ISS_TLE_RESPONSE

    response = client.get("/orbits/classify", params={"sat_id": "XSKZ-5603-1870-9019-3066"})

    assert response.status_code == 200
    assert response.json()["orbit_type"] == "LEO"
    assert "tle_age_days" in response.json()
    request = fake_satnogs.requests[0]
    assert request.url.path.endswith("/tle/")
    assert request.url.params["sat_id"] == "XSKZ-5603-1870-9019-3066"


def test_unknown_satellite_has_no_tle(fake_satnogs):
    fake_satnogs.body = []

    assert client.get("/orbits/classify", params={"sat_id": "NOPE"}).status_code == 404


def test_passes_default_to_the_reference_station(fake_satnogs):
    fake_satnogs.body = ISS_TLE_RESPONSE

    response = client.get(
        "/predictions/passes",
        params={"sat_id": "XSKZ-5603-1870-9019-3066", "start": "2026-10-21T00:00:00Z", "days": 2},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["station"]["lat"] == -34.5627
    assert body["min_elevation_deg"] == 10
    assert body["passes"] and {"aos", "tca", "los", "max_elevation_deg"} <= body["passes"][0].keys()


def test_passes_horizon_is_capped_at_seven_days(fake_satnogs):
    fake_satnogs.body = ISS_TLE_RESPONSE

    response = client.get("/predictions/passes", params={"sat_id": "X", "days": 8})

    assert response.status_code == 422


def test_ground_track_rejects_more_points_than_the_limit(fake_satnogs):
    fake_satnogs.body = ISS_TLE_RESPONSE

    response = client.get(
        "/predictions/groundtrack",
        params={"sat_id": "X", "start": "2026-10-21T00:00:00Z", "end": "2026-10-28T00:00:00Z", "step": 1},
    )

    assert response.status_code == 422
