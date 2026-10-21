"""Prediction vs. real SatNOGS observations, each one predicted with the TLE embedded in it.

SatNOGS' start/end/rise_azimuth/set_azimuth/max_altitude describe the scheduled window, which a
station may cut short with its own horizon; so elevation and azimuths are compared inside that
window, and start/end against the full pass at 0° (that error includes the scheduler's cut).
They come from SatNOGS' own SGP4 prediction, so agreement checks the implementation; max_altitude
and the azimuths are rounded to whole degrees.

SatNOGS stores no Doppler measurement per observation: observation_frequency − downlink_low is
the transmitter's oscillator drift (downlink_drift, in ppb). The predicted Doppler is reported,
not scored.
"""

from datetime import datetime, timedelta, timezone

import numpy as np

from services.doppler import doppler_shift_hz
from services.orbits import Station, find_passes, ground_track

WINDOW_STEP_S = 2
ERROR_METRICS = [
    "error_start_s",
    "error_end_s",
    "error_max_elevation_deg",
    "error_rise_azimuth_deg",
    "error_set_azimuth_deg",
]
REQUIRED_FIELDS = ["id", "tle1", "tle2", "station_lat", "station_lng", "start", "end", "max_altitude"]


def parse_time(iso: str) -> datetime:
    moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _azimuth_error(predicted: float, observed: float) -> float:
    return (predicted - observed + 180) % 360 - 180


def validate_observation(observation: dict) -> dict:
    tle = (observation["tle1"], observation["tle2"])
    station = Station(observation["station_lat"], observation["station_lng"], observation.get("station_alt") or 0)
    start, end = parse_time(observation["start"]), parse_time(observation["end"])

    window = ground_track(*tle, start, end, WINDOW_STEP_S, station)
    window += ground_track(*tle, end, end, WINDOW_STEP_S, station)
    max_elevation = max(point["elevation_deg"] for point in window)

    search_from = start - timedelta(minutes=30)
    hours = (end - search_from).total_seconds() / 3600 + 0.5
    passes = find_passes(*tle, station, search_from, days=hours / 24, min_elevation_deg=0)
    full_pass = next((p for p in passes if parse_time(p["aos"]) <= end and parse_time(p["los"]) >= start), None)

    result = {
        "observation_id": observation["id"],
        "station_name": observation.get("station_name"),
        "start": observation["start"],
        "end": observation["end"],
        "predicted_aos": full_pass["aos"] if full_pass else None,
        "predicted_los": full_pass["los"] if full_pass else None,
        "error_start_s": (parse_time(full_pass["aos"]) - start).total_seconds() if full_pass else None,
        "error_end_s": (parse_time(full_pass["los"]) - end).total_seconds() if full_pass else None,
        "predicted_max_elevation_deg": max_elevation,
        "error_max_elevation_deg": max_elevation - observation["max_altitude"],
        "error_rise_azimuth_deg": None,
        "error_set_azimuth_deg": None,
        "frequency_offset_hz": None,
        "predicted_max_doppler_hz": None,
    }
    if observation.get("rise_azimuth") is not None:
        result["error_rise_azimuth_deg"] = _azimuth_error(window[0]["azimuth_deg"], observation["rise_azimuth"])
    if observation.get("set_azimuth") is not None:
        result["error_set_azimuth_deg"] = _azimuth_error(window[-1]["azimuth_deg"], observation["set_azimuth"])

    f0 = observation.get("transmitter_downlink_low")
    if f0:
        if observation.get("observation_frequency"):
            result["frequency_offset_hz"] = observation["observation_frequency"] - f0
        result["predicted_max_doppler_hz"] = max(abs(doppler_shift_hz(f0, p["range_rate_km_s"])) for p in window)
    return result


def summarize(rows: list[dict], metrics: list[str] = ERROR_METRICS) -> dict:
    summary = {"count": len(rows)}
    for metric in metrics:
        values = np.array([row[metric] for row in rows if row.get(metric) is not None], dtype=float)
        if values.size == 0:
            summary[metric] = None
            continue
        summary[metric] = {
            "mean": float(values.mean()),
            "mean_abs": float(np.abs(values).mean()),
            "max_abs": float(np.abs(values).max()),
            "p95_abs": float(np.percentile(np.abs(values), 95)),
        }
    return summary


def validate_observations(observations: list[dict]) -> dict:
    """Skips, with a reason, observations missing data or inconsistent with their own TLE and station."""
    rows, skipped = [], []
    for observation in observations:
        missing = next((field for field in REQUIRED_FIELDS if observation.get(field) in (None, "")), None)
        if missing:
            skipped.append({"id": observation.get("id"), "reason": f"missing {missing}"})
            continue
        row = validate_observation(observation)
        if not row["predicted_max_elevation_deg"] >= 0:
            skipped.append({"id": row["observation_id"], "reason": "satellite below the horizon for its whole window (bad TLE or station)"})
            continue
        rows.append(row)
    return {"observations": rows, "summary": summarize(rows), "skipped": skipped}
