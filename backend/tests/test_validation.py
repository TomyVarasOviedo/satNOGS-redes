import json
from pathlib import Path

import pytest

from services.validation import summarize, validate_observation, validate_observations

OBSERVATIONS = json.loads((Path(__file__).parent / "lusat_good_observations.json").read_text())


def by_id(observation_id: int) -> dict:
    return next(o for o in OBSERVATIONS if o["id"] == observation_id)


def test_a_full_pass_matches_satnogs_within_rounding():
    result = validate_observation(by_id(15224792))

    assert result["error_max_elevation_deg"] == pytest.approx(0, abs=1)
    assert result["error_rise_azimuth_deg"] == pytest.approx(0, abs=1)
    assert result["error_set_azimuth_deg"] == pytest.approx(0, abs=1)
    assert abs(result["error_start_s"]) < 5 and abs(result["error_end_s"]) < 5


def test_every_real_observation_matches_inside_its_own_window():
    for observation in OBSERVATIONS:
        result = validate_observation(observation)

        assert abs(result["error_max_elevation_deg"]) <= 1.5, observation["id"]
        assert abs(result["error_rise_azimuth_deg"]) <= 2, observation["id"]
        assert abs(result["error_set_azimuth_deg"]) <= 2, observation["id"]


def test_azimuth_errors_wrap_around_north():
    observation = {**by_id(15224792), "rise_azimuth": 350.0}

    result = validate_observation(observation)

    assert result["error_rise_azimuth_deg"] == pytest.approx(9.85 - 350 + 360, abs=1)


def test_frequency_offset_is_reported_as_oscillator_drift_not_doppler():
    result = validate_observation(by_id(15224792))

    assert result["frequency_offset_hz"] == 437126350 - 437125000
    assert 8_000 < result["predicted_max_doppler_hz"] < 11_000


def test_observations_without_tle_or_station_are_skipped():
    report = validate_observations([{**by_id(15224792), "tle1": None}, by_id(15220664)])

    assert report["summary"]["count"] == 1
    assert report["skipped"] == [15224792]


def test_summary_statistics():
    rows = [{"error_start_s": e} for e in (-2, 0, 4)]

    stats = summarize(rows, ["error_start_s"])["error_start_s"]

    assert stats == pytest.approx({"mean": 2 / 3, "mean_abs": 2, "max_abs": 4, "p95_abs": 3.8})
