from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import httpx
import json
import uvicorn
from utils.config import SATNOGS_CONFIG, SERVER_CONFIG, RESILIENCE_CONFIG, SATELLITES_TO_MONITOR, REFERENCE_STATION, LINK_DEFAULTS
from services.satnogs import fetch_with_cache
from services.refresher import refresher
from services import doppler, linkbudget, orbits, validation


@asynccontextmanager
async def lifespan(app: FastAPI):
    refresher.start()
    yield
    refresher.stop()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def paginate(data, limit: int | None, offset: int | None):
    start = offset or 0
    end = (start + limit) if limit is not None else None
    if isinstance(data, list):
        return data[start:end]
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        data["results"] = data["results"][start:end]
        return data
    return data


def search_catalog(catalog: list, term: str) -> list:
    """SatNOGS DB ignores ?search=, so the full catalog is cached and filtered here."""
    term = term.strip().lower()

    def all_names(satellite: dict) -> list[str]:
        names = [satellite.get("name") or ""] + (satellite.get("names") or "").split(",")
        return [n.strip().lower() for n in names if n.strip()]

    matches = [s for s in catalog if any(term in n for n in all_names(s))]
    return sorted(matches, key=lambda s: term not in all_names(s))


def build_response(data: any, source: str, cache_age: int, status_code: int = 200) -> Response:
    return Response(
        content=json.dumps(data),
        status_code=status_code,
        media_type="application/json",
        headers={
            "X-Source": source,
            "X-Cache-Age": str(cache_age),
        },
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/satelite/{satelite_id}")
async def get_satelite_by_id(satelite_id: str):
    try:
        data, source, cache_age = await fetch_with_cache(
            endpoint="satellite_metadata",
            params={"sat_id": satelite_id},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_METADATA"],
            source="DB",
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?{urlencode(p)}",
        )
        return build_response(data, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/satelites/{satelite_name}")
async def get_satelite_by_name(
    satelite_name: str,
    limit: int | None = Query(10, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    try:
        catalog, source, cache_age = await fetch_with_cache(
            endpoint="satellite_catalog",
            params={},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_METADATA"],
            source="DB",
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/",
        )
        matches = search_catalog(catalog, satelite_name)
        return build_response(paginate(matches, limit, offset), source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/observations/{satelite_id}")
async def get_observations_by_satelite_id(
    satelite_id: str,
    limit: int | None = Query(10, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    try:
        data, source, cache_age = await fetch_with_cache(
            endpoint="observations",
            params={"sat_id": satelite_id},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_OBSERVATIONS"],
            source="NETWORK",
            url_builder=lambda p: f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/?{urlencode(p)}",
        )
        if isinstance(data, list):
            data = paginate(data, limit, offset)
        return build_response(data, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/observations/id/{id}")
async def get_observations_by_id(id: int):
    try:
        data, source, cache_age = await fetch_with_cache(
            endpoint="observation_by_id",
            params={"id": id},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_OBSERVATIONS"],
            source="NETWORK",
            url_builder=lambda p: f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/{p['id']}/",
        )
        return build_response(data, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/telemetry/{satelite_id}")
async def get_telemetry_by_satelite_id(
    satelite_id: int,
    limit: int | None = Query(10, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    try:
        data, source, cache_age = await fetch_with_cache(
            endpoint="telemetry",
            params={"satellite": satelite_id},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_TELEMETRY"],
            source="DB",
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/telemetry/?{urlencode(p)}",
        )
        if isinstance(data, list):
            data = paginate(data, limit, offset)
        return build_response(data, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


MAX_GROUND_TRACK_POINTS = 5000


async def fetch_current_tle(sat_id: str) -> tuple[dict | None, str, int]:
    data, source, cache_age = await fetch_with_cache(
        endpoint="tle",
        params={"sat_id": sat_id},
        ttl=RESILIENCE_CONFIG["DEFAULT_TTL_TLE"],
        source="DB",
        url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/tle/?{urlencode(p)}",
    )
    tle = data[0] if isinstance(data, list) and data else None
    return tle, source, cache_age


def tle_not_found(sat_id: str, source: str, cache_age: int) -> Response:
    return build_response({"error": f"No TLE found for sat_id {sat_id}"}, source, cache_age, 404)


def utc(moment: datetime | None) -> datetime:
    if moment is None:
        return datetime.now(timezone.utc)
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def station_from(lat: float | None, lng: float | None, alt: float | None) -> orbits.Station:
    return orbits.Station(
        lat=REFERENCE_STATION["lat"] if lat is None else lat,
        lng=REFERENCE_STATION["lng"] if lng is None else lng,
        alt_m=REFERENCE_STATION["alt_m"] if alt is None else alt,
    )


async def fetch_transmitters_or_empty(sat_id: str) -> list[dict]:
    """Transmitters only enrich a prediction, so a SatNOGS failure degrades to no link data."""
    try:
        data, _, _ = await fetch_with_cache(
            endpoint="transmitters",
            params={"sat_id": sat_id},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_METADATA"],
            source="DB",
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/transmitters/?{urlencode(p)}",
        )
        return data if isinstance(data, list) else []
    except Exception:
        return []


def pass_link(tle: dict, station: orbits.Station, satellite_pass: dict, transmitter: dict | None) -> dict | None:
    if transmitter is None:
        return None

    def margin_at(iso: str) -> float | None:
        moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        distance = orbits.ground_track(tle["tle1"], tle["tle2"], moment, moment, 1, station)[0]["range_km"]
        budget = linkbudget.link_budget(
            distance, doppler.downlink_frequency_hz(transmitter), baud=transmitter.get("baud"), mode=transmitter.get("mode"), **LINK_DEFAULTS
        )
        return budget["margin_db"]

    return {
        "transmitter_uuid": transmitter.get("uuid"),
        "description": transmitter.get("description"),
        "freq_hz": doppler.downlink_frequency_hz(transmitter),
        "mode": transmitter.get("mode"),
        "baud": transmitter.get("baud"),
        "margin_at_aos_db": margin_at(satellite_pass["aos"]),
        "margin_at_tca_db": margin_at(satellite_pass["tca"]),
    }


@app.get("/orbits/classify")
async def classify_orbit(sat_id: str):
    try:
        tle, source, cache_age = await fetch_current_tle(sat_id)
        if tle is None:
            return tle_not_found(sat_id, source, cache_age)
        summary = orbits.orbit_summary(tle["tle1"], tle["tle2"], REFERENCE_STATION["min_elevation_deg"])
        age = datetime.now(timezone.utc) - orbits.tle_epoch(tle["tle1"], tle["tle2"])
        summary.update(sat_id=sat_id, name=tle.get("tle0"), tle_age_days=round(age.total_seconds() / 86400, 2))
        return build_response(summary, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/predictions/passes")
async def predict_passes(
    sat_id: str,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    alt: float | None = Query(None),
    horizon_deg: float | None = Query(None, ge=0, lt=90),
    days: float = Query(2, gt=0, le=7),
    start: datetime | None = Query(None),
):
    try:
        tle, source, cache_age = await fetch_current_tle(sat_id)
        if tle is None:
            return tle_not_found(sat_id, source, cache_age)
        station = station_from(lat, lng, alt)
        min_elevation = REFERENCE_STATION["min_elevation_deg"] if horizon_deg is None else horizon_deg
        passes = orbits.find_passes(tle["tle1"], tle["tle2"], station, utc(start), days, min_elevation)
        transmitter = doppler.pick_transmitter(await fetch_transmitters_or_empty(sat_id))
        for p in passes:
            p["link"] = pass_link(tle, station, p, transmitter)
        return build_response(
            {
                "sat_id": sat_id,
                "station": {"lat": station.lat, "lng": station.lng, "alt_m": station.alt_m},
                "min_elevation_deg": min_elevation,
                "tle_epoch": orbits.tle_epoch(tle["tle1"], tle["tle2"]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "passes": passes,
            },
            source,
            cache_age,
        )
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/predictions/groundtrack")
async def predict_ground_track(
    sat_id: str,
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    step: int = Query(60, ge=1),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    alt: float | None = Query(None),
):
    start = utc(start)
    end = utc(end) if end else start + timedelta(minutes=100)
    points = int((end - start).total_seconds() // step) + 1
    if end < start or points > MAX_GROUND_TRACK_POINTS:
        return build_response(
            {"error": f"Window must be non-negative and at most {MAX_GROUND_TRACK_POINTS} points (got {points})"},
            "error",
            0,
            422,
        )
    try:
        tle, source, cache_age = await fetch_current_tle(sat_id)
        if tle is None:
            return tle_not_found(sat_id, source, cache_age)
        track = orbits.ground_track(tle["tle1"], tle["tle2"], start, end, step, station_from(lat, lng, alt))
        return build_response(track, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/predictions/doppler")
async def predict_doppler(
    sat_id: str,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    alt: float | None = Query(None),
    horizon_deg: float | None = Query(None, ge=0, lt=90),
    start: datetime | None = Query(None),
    days: float = Query(2, gt=0, le=7),
    freq_hz: float | None = Query(None, gt=0),
    transmitter_uuid: str | None = Query(None),
    step: int = Query(10, ge=1, le=300),
):
    """Frequency to tune along the next pass that starts (or is under way) after `start`."""
    try:
        tle, source, cache_age = await fetch_current_tle(sat_id)
        if tle is None:
            return tle_not_found(sat_id, source, cache_age)
        station = station_from(lat, lng, alt)
        min_elevation = REFERENCE_STATION["min_elevation_deg"] if horizon_deg is None else horizon_deg
        passes = orbits.find_passes(tle["tle1"], tle["tle2"], station, utc(start), days, min_elevation)
        if not passes:
            return build_response({"error": f"No pass above {min_elevation}° in the next {days} days"}, source, cache_age, 404)

        transmitter = None
        if freq_hz is None:
            transmitter = doppler.pick_transmitter(await fetch_transmitters_or_empty(sat_id), transmitter_uuid)
            if transmitter is None:
                return build_response({"error": "No downlink transmitter known; pass freq_hz"}, source, cache_age, 404)
            freq_hz = doppler.downlink_frequency_hz(transmitter)

        satellite_pass = passes[0]
        curve = doppler.doppler_curve(
            tle["tle1"],
            tle["tle2"],
            station,
            datetime.fromisoformat(satellite_pass["aos"].replace("Z", "+00:00")),
            datetime.fromisoformat(satellite_pass["los"].replace("Z", "+00:00")),
            freq_hz,
            step,
        )
        baud, mode = (transmitter.get("baud"), transmitter.get("mode")) if transmitter else (None, None)
        for point in curve["points"]:
            point["margin_db"] = linkbudget.link_budget(point["range_km"], freq_hz, baud=baud, mode=mode, **LINK_DEFAULTS)["margin_db"]
        return build_response({"sat_id": sat_id, "pass": satellite_pass, "transmitter": transmitter, **curve}, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/linkbudget")
async def calculate_link_budget(
    freq_hz: float = Query(..., gt=0),
    distance_km: float | None = Query(None, gt=0),
    elevation_deg: float | None = Query(None, ge=0, le=90),
    altitude_km: float | None = Query(None, gt=0),
    eirp_dbw: float = Query(LINK_DEFAULTS["eirp_dbw"]),
    gain_dbi: float = Query(LINK_DEFAULTS["gain_dbi"]),
    noise_k: float = Query(LINK_DEFAULTS["noise_temp_k"], gt=0),
    losses_db: float = Query(LINK_DEFAULTS["losses_db"], ge=0),
    baud: float = Query(1200, ge=0),
    mode: str = Query("BPSK"),
):
    """Editable link budget: give distance_km, or elevation_deg + altitude_km for the slant range."""
    if distance_km is None:
        if elevation_deg is None or altitude_km is None:
            return build_response({"error": "Give distance_km, or elevation_deg and altitude_km"}, "error", 0, 422)
        distance_km = linkbudget.slant_range_km(elevation_deg, altitude_km)
    budget = linkbudget.link_budget(distance_km, freq_hz, eirp_dbw, gain_dbi, noise_k, baud, mode, losses_db)
    return build_response(budget, "computed", 0)


VALIDATION_NOTES = [
    "Each observation is predicted with the TLE embedded in it, at its own station.",
    "Elevation and azimuths are compared inside the observation's scheduled window; "
    "SatNOGS rounds them to whole degrees.",
    "error_start_s/error_end_s compare against the full pass at 0°: they include the station "
    "scheduler cutting the window, not only prediction error.",
    "SatNOGS start/end come from its own SGP4 prediction, so agreement validates the implementation, "
    "not the orbit itself.",
    "SatNOGS stores no measured Doppler: observation_frequency − downlink_low is the transmitter's "
    "oscillator drift (ppb). The predicted Doppler is reported, not scored.",
]


@app.get("/validation/satellite")
async def validate_satellite(
    sat_id: str,
    days: float = Query(7, gt=0, le=30),
    end: datetime | None = Query(None),
):
    """Predicted passes vs. the satellite's most recent good SatNOGS observations in the period."""
    try:
        data, source, cache_age = await fetch_with_cache(
            endpoint="observations_good",
            params={"sat_id": sat_id, "status": "good"},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_OBSERVATIONS"],
            source="NETWORK",
            url_builder=lambda p: f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/?{urlencode(p)}",
        )
        end = utc(end)
        begin = end - timedelta(days=days)
        in_period = [
            o for o in (data if isinstance(data, list) else [])
            if o.get("start") and begin <= datetime.fromisoformat(o["start"].replace("Z", "+00:00")) <= end
        ]
        report = validation.validate_observations(in_period)
        return build_response(
            {
                "sat_id": sat_id,
                "period": {"start": begin.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": end.strftime("%Y-%m-%dT%H:%M:%SZ")},
                **report,
                "notes": VALIDATION_NOTES,
            },
            source,
            cache_age,
        )
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/satellites/monitored")
async def get_monitored_satellites():
    return build_response(SATELLITES_TO_MONITOR, "config", 0)


if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_CONFIG['HOST'], port=int(SERVER_CONFIG['PORT']))