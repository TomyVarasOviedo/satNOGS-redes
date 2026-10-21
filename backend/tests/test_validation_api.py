import json
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
OBSERVATIONS = json.loads((Path(__file__).parent / "lusat_good_observations.json").read_text())


def test_validation_covers_good_observations_in_the_period(fake_satnogs):
    fake_satnogs.routes = {"/observations/": OBSERVATIONS}

    response = client.get(
        "/validation/satellite",
        params={"sat_id": "ZDPY-4221-9426-0630-5344", "days": 7, "end": "2026-10-18T00:00:00Z"},
    )

    body = response.json()
    assert response.status_code == 200
    assert [o["observation_id"] for o in body["observations"]] == [15224792, 15220664, 15203946, 15193508]
    assert body["summary"]["count"] == 4
    assert abs(body["summary"]["error_max_elevation_deg"]["mean_abs"]) < 1.5
    request = fake_satnogs.requests[0]
    assert request.url.params["status"] == "good"
    assert request.url.params["sat_id"] == "ZDPY-4221-9426-0630-5344"


def test_validation_period_is_capped(fake_satnogs):
    assert client.get("/validation/satellite", params={"sat_id": "X", "days": 31}).status_code == 422
