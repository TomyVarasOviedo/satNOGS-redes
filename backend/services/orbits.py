import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

EARTH_RADIUS_KM = 6371.0
MU_KM3_S2 = 398600.4418
LEO_MAX_KM = 2000
GEO_ALTITUDE_KM = 35786
GEO_TOLERANCE_KM = 500
HEO_MIN_ECCENTRICITY = 0.25

RISE, CULMINATE, SET = 0, 1, 2

timescale = load.timescale()


@dataclass(frozen=True)
class Station:
    lat: float
    lng: float
    alt_m: float

    def topos(self):
        return wgs84.latlon(self.lat, self.lng, elevation_m=self.alt_m)


def _satellite(tle1: str, tle2: str) -> EarthSatellite:
    return EarthSatellite(tle1, tle2, ts=timescale)


def _iso(t) -> str:
    return t.utc_datetime().strftime("%Y-%m-%dT%H:%M:%SZ")


def orbit_type(altitude_km: float, eccentricity: float) -> str:
    """LEO below 2000 km (common definition; the course's 640–1600 km range would leave the ISS out)."""
    if eccentricity > HEO_MIN_ECCENTRICITY:
        return "HEO"
    if altitude_km < LEO_MAX_KM:
        return "LEO"
    if abs(altitude_km - GEO_ALTITUDE_KM) <= GEO_TOLERANCE_KM:
        return "GEO"
    if altitude_km < GEO_ALTITUDE_KM:
        return "MEO"
    return "HEO"


def footprint_radius_km(altitude_km: float, min_elevation_deg: float) -> float:
    """λ = arccos(R/(R+h)·cos ε) − ε; ground radius R·λ (TFI §3.5)."""
    eps = math.radians(min_elevation_deg)
    central_angle = math.acos(EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude_km) * math.cos(eps)) - eps
    return EARTH_RADIUS_KM * central_angle


def orbit_summary(tle1: str, tle2: str, min_elevation_deg: float = 10) -> dict:
    """Period from mean motion, semi-major axis from Kepler's third law: a = (μ·(T/2π)²)^(1/3)."""
    satellite = _satellite(tle1, tle2)
    model = satellite.model
    mean_motion_rev_day = model.no_kozai * 1440 / (2 * math.pi)
    period_s = 86400 / mean_motion_rev_day
    semi_major_axis_km = (MU_KM3_S2 * (period_s / (2 * math.pi)) ** 2) ** (1 / 3)
    altitude_km = semi_major_axis_km - EARTH_RADIUS_KM
    eccentricity = model.ecco

    return {
        "orbit_type": orbit_type(altitude_km, eccentricity),
        "period_min": period_s / 60,
        "mean_motion_rev_day": mean_motion_rev_day,
        "semi_major_axis_km": semi_major_axis_km,
        "altitude_km": altitude_km,
        "perigee_km": semi_major_axis_km * (1 - eccentricity) - EARTH_RADIUS_KM,
        "apogee_km": semi_major_axis_km * (1 + eccentricity) - EARTH_RADIUS_KM,
        "eccentricity": eccentricity,
        "inclination_deg": math.degrees(model.inclo),
        "footprint_radius_km": footprint_radius_km(altitude_km, min_elevation_deg),
        "tle_epoch": _iso(satellite.epoch),
    }


def tle_epoch(tle1: str, tle2: str) -> datetime:
    return _satellite(tle1, tle2).epoch.utc_datetime()


def find_passes(
    tle1: str,
    tle2: str,
    station: Station,
    start: datetime,
    days: float,
    min_elevation_deg: float,
) -> list[dict]:
    """AOS/LOS are exact crossings of the elevation mask (skyfield find_events); passes cut by the window are dropped."""
    satellite = _satellite(tle1, tle2)
    topos = station.topos()
    relative = satellite - topos
    t0 = timescale.from_datetime(start)
    t1 = timescale.from_datetime(start + timedelta(days=days))
    times, events = satellite.find_events(topos, t0, t1, altitude_degrees=min_elevation_deg)

    passes = []
    current = None
    for t, event in zip(times, events):
        if event == RISE:
            current = {"aos": t, "tca": None, "max_elevation": -90.0}
        elif current is None:
            continue
        elif event == CULMINATE:
            elevation = relative.at(t).altaz()[0].degrees
            if elevation > current["max_elevation"]:
                current["tca"], current["max_elevation"] = t, elevation
        elif event == SET and current["tca"] is not None:
            passes.append(_describe_pass(relative, current, t))
            current = None
    return passes


def _describe_pass(relative, current: dict, los) -> dict:
    aos = current["aos"]
    return {
        "aos": _iso(aos),
        "tca": _iso(current["tca"]),
        "los": _iso(los),
        "duration_s": round((los - aos) * 86400),
        "max_elevation_deg": round(float(current["max_elevation"]), 2),
        "aos_azimuth_deg": round(float(relative.at(aos).altaz()[1].degrees), 2),
        "los_azimuth_deg": round(float(relative.at(los).altaz()[1].degrees), 2),
    }


def ground_track(
    tle1: str,
    tle2: str,
    start: datetime,
    end: datetime,
    step_s: int,
    station: Station | None = None,
) -> list[dict]:
    satellite = _satellite(tle1, tle2)
    offsets_s = np.arange(0, (end - start).total_seconds() + 1e-9, step_s)
    times = timescale.from_datetime(start) + offsets_s / 86400

    geocentric = satellite.at(times)
    lat, lng = wgs84.latlon_of(geocentric)
    alt_km = wgs84.height_of(geocentric).km
    track = [
        {"t": _iso(times[i]), "lat": float(lat.degrees[i]), "lng": float(lng.degrees[i]), "alt_km": float(alt_km[i])}
        for i in range(len(offsets_s))
    ]

    if station is not None:
        topocentric = (satellite - station.topos()).at(times)
        elevation, azimuth, distance = topocentric.altaz()
        range_rate = topocentric.frame_latlon_and_rates(station.topos())[5].km_per_s
        for i, point in enumerate(track):
            point.update(
                elevation_deg=float(elevation.degrees[i]),
                azimuth_deg=float(azimuth.degrees[i]),
                range_km=float(distance.km[i]),
                range_rate_km_s=float(range_rate[i]),
            )
    return track
