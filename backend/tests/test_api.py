from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


CATALOG = [
    {"name": "NOAA 18", "names": ""},
    {"name": "LUSAT", "names": "LO-19, LUSAT-OSCAR 19"},
    {"name": "NOAA 19", "names": ""},
]


def names_in(response):
    return [s["name"] for s in response.json()]


def test_search_returns_only_satellites_whose_name_matches(fake_satnogs):
    fake_satnogs.body = CATALOG

    assert names_in(client.get("/satelites/noaa")) == ["NOAA 18", "NOAA 19"]


def test_search_matches_alternate_names_and_ranks_exact_match_first(fake_satnogs):
    fake_satnogs.body = CATALOG + [{"name": "NOAA 19 LO-19 MIRROR", "names": ""}]

    assert names_in(client.get("/satelites/lo-19")) == ["LUSAT", "NOAA 19 LO-19 MIRROR"]


def test_searches_share_one_cached_catalog_download(fake_satnogs):
    fake_satnogs.body = CATALOG

    client.get("/satelites/noaa")
    client.get("/satelites/lusat")

    assert len(fake_satnogs.requests) == 1


def test_path_ids_cannot_inject_query_parameters(fake_satnogs):
    client.get("/observations/ZDPY&status=bad")

    assert fake_satnogs.requests[0].url.params["sat_id"] == "ZDPY&status=bad"


def test_a_failed_search_is_retried_on_the_next_request(fake_satnogs):
    fake_satnogs.status = 503
    assert client.get("/satelites/LUSAT").status_code == 500

    fake_satnogs.status = 200
    fake_satnogs.body = [{"name": "LUSAT"}]
    response = client.get("/satelites/LUSAT")

    assert response.status_code == 200
    assert response.json() == [{"name": "LUSAT"}]


def test_a_failed_telemetry_lookup_is_retried_on_the_next_request(fake_satnogs):
    fake_satnogs.status = 503
    assert client.get("/telemetry/20442").status_code == 500

    fake_satnogs.status = 200
    fake_satnogs.body = [{"frame": "AB"}]

    assert client.get("/telemetry/20442").status_code == 200
