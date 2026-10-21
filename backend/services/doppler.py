from datetime import datetime

from services.linkbudget import REQUIRED_EBN0_DB
from services.orbits import Station, ground_track

SPEED_OF_LIGHT_M_S = 299_792_458


def doppler_shift_hz(f0_hz: float, range_rate_km_s: float) -> float:
    """Δf = −f0·v_r/c, with v_r > 0 when the satellite moves away (TFI §3.6)."""
    return -f0_hz * range_rate_km_s * 1000 / SPEED_OF_LIGHT_M_S


def downlink_frequency_hz(transmitter: dict) -> float:
    """SatNOGS' downlink_drift is the transmitter's oscillator offset in ppb, not Doppler."""
    drift_ppb = transmitter.get("downlink_drift") or 0
    return transmitter["downlink_low"] * (1 + drift_ppb / 1e9)


def pick_transmitter(transmitters: list[dict], uuid: str | None = None) -> dict | None:
    """The requested uuid, else an alive downlink with a digital mode we can budget, else any alive downlink."""
    downlinks = [t for t in transmitters if t.get("downlink_low")]
    if uuid:
        return next((t for t in downlinks if t.get("uuid") == uuid), None)
    alive = [t for t in downlinks if t.get("alive")]
    digital = [t for t in alive if (t.get("mode") or "").upper() in REQUIRED_EBN0_DB and (t.get("baud") or 0) > 0]
    return (digital or alive or [None])[0]


def doppler_curve(
    tle1: str,
    tle2: str,
    station: Station,
    aos: datetime,
    los: datetime,
    f0_hz: float,
    step_s: int = 10,
) -> dict:
    track = ground_track(tle1, tle2, aos, los, step_s, station)
    if track[-1]["t"] != los.strftime("%Y-%m-%dT%H:%M:%SZ"):
        track += ground_track(tle1, tle2, los, los, step_s, station)

    points = []
    for point in track:
        shift = doppler_shift_hz(f0_hz, point["range_rate_km_s"])
        points.append(
            {
                "t": point["t"],
                "elevation_deg": point["elevation_deg"],
                "range_km": point["range_km"],
                "range_rate_km_s": point["range_rate_km_s"],
                "shift_hz": shift,
                "frequency_hz": f0_hz + shift,
            }
        )

    rates = [((b["shift_hz"] - a["shift_hz"]) / _seconds_between(a["t"], b["t"]), a["t"]) for a, b in zip(points, points[1:])]
    max_rate, max_rate_at = min(rates) if rates else (0.0, points[0]["t"])

    return {
        "f0_hz": f0_hz,
        "aos_frequency_hz": points[0]["frequency_hz"],
        "los_frequency_hz": points[-1]["frequency_hz"],
        "max_shift_hz": max(abs(p["shift_hz"]) for p in points),
        "max_rate_hz_s": max_rate,
        "max_rate_at": max_rate_at,
        "points": points,
    }


def _seconds_between(start_iso: str, end_iso: str) -> float:
    return (datetime.fromisoformat(end_iso.replace("Z", "+00:00")) - datetime.fromisoformat(start_iso.replace("Z", "+00:00"))).total_seconds()
