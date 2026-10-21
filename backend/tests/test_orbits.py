from datetime import datetime, timedelta, timezone

import pytest

from services.orbits import (
    Station,
    find_passes,
    footprint_radius_km,
    ground_track,
    orbit_summary,
    orbit_type,
)
from tests.tle_fixtures import GOES_16, ISS, LUSAT_OBSERVATION

BUENOS_AIRES = Station(lat=-34.5627, lng=-58.4566, alt_m=25)


def parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def test_iss_is_leo_with_period_from_mean_motion():
    summary = orbit_summary(*ISS)

    assert summary["orbit_type"] == "LEO"
    assert summary["period_min"] == pytest.approx(1440 / 15.48973463, abs=0.01)
    assert 400 < summary["altitude_km"] < 440
    assert summary["inclination_deg"] == pytest.approx(51.633, abs=0.001)


def test_goes_16_is_geostationary():
    summary = orbit_summary(*GOES_16)

    assert summary["orbit_type"] == "GEO"
    assert summary["altitude_km"] == pytest.approx(35786, abs=50)


@pytest.mark.parametrize(
    "altitude_km, eccentricity, expected",
    [
        (550, 0.001, "LEO"),
        (20200, 0.01, "MEO"),
        (35786, 0.0002, "GEO"),
        (20000, 0.72, "HEO"),
    ],
)
def test_orbit_type_by_altitude_and_eccentricity(altitude_km, eccentricity, expected):
    assert orbit_type(altitude_km, eccentricity) == expected


def test_footprint_radius_matches_the_tfi_worked_example():
    assert footprint_radius_km(550, 10) == pytest.approx(1670, abs=10)


def test_predicted_pass_matches_a_real_satnogs_observation():
    obs = LUSAT_OBSERVATION
    station = Station(obs["station_lat"], obs["station_lng"], obs["station_alt"])
    start = parse(obs["start"]) - timedelta(minutes=30)

    passes = find_passes(obs["tle1"], obs["tle2"], station, start, days=1 / 24, min_elevation_deg=0)

    assert len(passes) == 1
    predicted = passes[0]
    assert predicted["max_elevation_deg"] == pytest.approx(obs["max_altitude"], abs=1)
    assert predicted["aos_azimuth_deg"] == pytest.approx(obs["rise_azimuth"], abs=2)
    assert predicted["los_azimuth_deg"] == pytest.approx(obs["set_azimuth"], abs=2)
    assert abs((parse(predicted["aos"]) - parse(obs["start"])).total_seconds()) < 60
    assert abs((parse(predicted["los"]) - parse(obs["end"])).total_seconds()) < 60


def test_passes_start_and_end_on_the_elevation_mask():
    start = datetime(2026, 10, 21, tzinfo=timezone.utc)

    passes = find_passes(*ISS, BUENOS_AIRES, start, days=2, min_elevation_deg=10)

    assert passes
    for p in passes:
        assert start <= parse(p["aos"]) < parse(p["tca"]) < parse(p["los"]) <= start + timedelta(days=2)
        assert p["max_elevation_deg"] >= 10
        assert p["duration_s"] == pytest.approx((parse(p["los"]) - parse(p["aos"])).total_seconds(), abs=1)
        track = ground_track(*ISS, parse(p["aos"]), parse(p["aos"]), 60, BUENOS_AIRES)
        assert track[0]["elevation_deg"] == pytest.approx(10, abs=0.1)


def test_ground_track_samples_every_step_and_stays_within_inclination():
    start = datetime(2026, 10, 21, tzinfo=timezone.utc)

    track = ground_track(*ISS, start, start + timedelta(minutes=90), 60)

    assert len(track) == 91
    assert all(abs(point["lat"]) <= 51.633 + 0.5 for point in track)
    assert all(400 < point["alt_km"] < 440 for point in track)
    assert "elevation_deg" not in track[0]


def test_ground_track_relative_to_a_station_includes_range_rate():
    start = datetime(2026, 10, 21, tzinfo=timezone.utc)

    point = ground_track(*ISS, start, start, 60, BUENOS_AIRES)[0]

    assert {"elevation_deg", "azimuth_deg", "range_km", "range_rate_km_s"} <= point.keys()
    assert abs(point["range_rate_km_s"]) < 8
