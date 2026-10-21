from datetime import timedelta

import pytest

from services.doppler import doppler_curve, doppler_shift_hz, downlink_frequency_hz, pick_transmitter
from services.orbits import Station, find_passes
from tests.test_orbits import parse
from tests.tle_fixtures import LUSAT_OBSERVATION, LUSAT_TRANSMITTERS


def high_lusat_pass():
    obs = LUSAT_OBSERVATION
    station = Station(obs["station_lat"], obs["station_lng"], obs["station_alt"])
    p = find_passes(obs["tle1"], obs["tle2"], station, parse(obs["start"]) - timedelta(minutes=30), 1 / 24, 0)[0]
    return obs, station, p


def test_shift_is_minus_f0_times_radial_velocity_over_c():
    assert doppler_shift_hz(437.15e6, 7.0) == pytest.approx(-437.15e6 * 7000 / 299_792_458)
    assert doppler_shift_hz(437.15e6, -7.0) > 0


def test_curve_starts_high_crosses_nominal_at_tca_and_ends_low():
    obs, station, p = high_lusat_pass()

    curve = doppler_curve(obs["tle1"], obs["tle2"], station, parse(p["aos"]), parse(p["los"]), 437.15e6, step_s=5)
    shifts = [point["shift_hz"] for point in curve["points"]]

    assert shifts[0] > 0 > shifts[-1]
    assert 8_000 < curve["max_shift_hz"] < 11_000
    crossing = next(pt for pt, nxt in zip(curve["points"], curve["points"][1:]) if pt["shift_hz"] > 0 >= nxt["shift_hz"])
    assert abs((parse(crossing["t"]) - parse(p["tca"])).total_seconds()) <= 10
    assert curve["points"][-1]["t"] == p["los"]
    assert curve["aos_frequency_hz"] == pytest.approx(437.15e6 + shifts[0])


def test_the_steepest_frequency_change_is_near_tca():
    obs, station, p = high_lusat_pass()

    curve = doppler_curve(obs["tle1"], obs["tle2"], station, parse(p["aos"]), parse(p["los"]), 437.15e6, step_s=5)

    assert curve["max_rate_hz_s"] < 0
    assert abs((parse(curve["max_rate_at"]) - parse(p["tca"])).total_seconds()) <= 30


def test_pick_transmitter_prefers_an_alive_digital_downlink():
    assert pick_transmitter(LUSAT_TRANSMITTERS)["description"] == "BPSK 1k2 Transceiver"
    assert pick_transmitter(LUSAT_TRANSMITTERS, uuid="ZAKErADdWKpMiDjvKKhmmB")["mode"] == "CW"
    assert pick_transmitter([]) is None


def test_downlink_frequency_applies_the_oscillator_drift_in_ppb():
    cw = LUSAT_TRANSMITTERS[1]

    assert downlink_frequency_hz(cw) == pytest.approx(437_125_000 * (1 + 3088e-9))
    assert downlink_frequency_hz(LUSAT_TRANSMITTERS[0]) == 437_150_000
