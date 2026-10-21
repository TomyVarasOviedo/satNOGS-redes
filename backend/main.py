from contextlib import asynccontextmanager
from urllib.parse import urlencode
from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import httpx
import json
import uvicorn
from utils.config import SATNOGS_CONFIG, SERVER_CONFIG, RESILIENCE_CONFIG, SATELLITES_TO_MONITOR
from services.satnogs import fetch_with_cache
from services.refresher import refresher


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


@app.get("/satellites/monitored")
async def get_monitored_satellites():
    return build_response(SATELLITES_TO_MONITOR, "config", 0)


if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_CONFIG['HOST'], port=int(SERVER_CONFIG['PORT']))