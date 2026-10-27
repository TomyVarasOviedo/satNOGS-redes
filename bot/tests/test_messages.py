from zoneinfo import ZoneInfo

from messages import (
    chunk,
    format_agenda,
    format_help,
    format_normal_mode,
    format_orbit,
    format_pass_alert,
    format_passes,
    format_test_mode,
    format_tle_warning,
)

UTC = ZoneInfo("UTC")

PASS = {
    "aos": "2026-10-27T18:30:00Z",
    "tca": "2026-10-27T18:34:00Z",
    "los": "2026-10-27T18:38:00Z",
    "duration_s": 480,
    "max_elevation_deg": 76,
    "aos_azimuth_deg": 12,
    "los_azimuth_deg": 171,
    "aos_clipped": False,
    "los_clipped": False,
    "link": {
        "margin_at_aos_db": 20.4,
        "margin_at_tca_db": 29.7,
        "freq_hz": 437150000,
        "mode": "BPSK",
        "baud": 1200,
    },
}
DOPPLER = {
    "f0_hz": 437150000,
    "aos_frequency_hz": 437158000,
    "los_frequency_hz": 437142000,
}
ORBIT = {
    "orbit_type": "LEO",
    "period_min": 100.4,
    "altitude_km": 785,
    "inclination_deg": 98.9,
    "footprint_radius_km": 2084,
    "tle_age_days": 2.5,
}


def test_pass_alert_includes_time_doppler_and_margin():
    text = format_pass_alert("LUSAT", PASS, DOPPLER, UTC, "live", 14)

    assert "LUSAT" in text
    assert "Pasa en 14 min" in text
    assert "437.158 MHz" in text
    assert "437.150 MHz" in text
    assert "437.142 MHz" in text
    assert "+29.7 dB" in text
    assert "decodable" in text


def test_pass_alert_flags_a_pass_without_margin():
    pass_without_margin = {**PASS, "link": {**PASS["link"], "margin_at_tca_db": -2.0}}

    text = format_pass_alert("LUSAT", pass_without_margin, None, UTC)

    assert "sin margen" in text
    assert "decodable" not in text


def test_pass_alert_escapes_the_satellite_name():
    text = format_pass_alert("<LUSAT & Cía>", PASS, None, UTC)

    assert "&lt;LUSAT &amp; Cía&gt;" in text
    assert "<LUSAT" not in text


def test_pass_alert_mentions_cached_data():
    text = format_pass_alert("LUSAT", PASS, None, UTC, "stale")

    assert "caché" in text


def test_agenda_lists_each_satellite_and_marks_empty_ones():
    text = format_agenda([("LUSAT", [PASS]), ("ISS", [])], UTC)

    assert "LUSAT" in text
    assert "ISS" in text
    assert "sin pases" in text


def test_passes_list_includes_the_date():
    text = format_passes([("LUSAT", [PASS])], UTC)

    assert "27/10" in text
    assert "18:30 UTC" in text


def test_orbit_and_tle_warning():
    orbit_text = format_orbit("LUSAT", ORBIT, tle_max_age_days=7)
    warning_text = format_tle_warning("LUSAT", {**ORBIT, "tle_age_days": 9.2}, 7)

    assert "LEO" in orbit_text
    assert "100.4 min" in orbit_text
    assert "desactualizado" in warning_text
    assert "9.2 días" in warning_text


def test_help_escapes_names_and_lists_commands():
    text = format_help(["LUSAT", "<ISS>"])

    assert "/pases" in text
    assert "/test" in text
    assert "/stop" in text
    assert "&lt;ISS&gt;" in text


def test_test_and_normal_mode_messages():
    test_text = format_test_mode(5, 1, 2)
    normal_text = format_normal_mode(5, 15)

    assert "Modo prueba activado" in test_text
    assert "cada 5 s" in test_text
    assert "T-1 min" in test_text
    assert "2" in test_text
    assert "Modo prueba desactivado" in normal_text
    assert "cada 5 min" in normal_text
    assert "T-15 min" in normal_text


def test_chunk_keeps_every_message_under_the_limit():
    text = "\n".join(f"line {index} " + "x" * 50 for index in range(200))

    parts = chunk(text, limit=500)

    assert all(len(part) <= 500 for part in parts)
    assert "".join(parts) == text
