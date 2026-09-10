from contextlib import asynccontextmanager
from functools import wraps
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


def async_lru_cache(maxsize: int = 128):
    def decorator(func):
        cache = {}
        order = []

        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = args + tuple(sorted(kwargs.items()))
            if key not in cache:
                if len(order) >= maxsize:
                    oldest = order.pop(0)
                    cache.pop(oldest, None)
                cache[key] = await func(*args, **kwargs)
                order.append(key)
            else:
                order.remove(key)
                order.append(key)
            return cache[key]
        return wrapper
    return decorator


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
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?sat_id={p['sat_id']}",
        )
        return build_response(data, source, cache_age)
    except Exception as e:
        return build_response({"error": str(e)}, "error", 0, 500)


@app.get("/satelites/{satelite_name}")
@async_lru_cache(maxsize=128)
async def get_satelite_by_name(
    satelite_name: str,
    limit: int | None = Query(10, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    try:
        data, source, cache_age = await fetch_with_cache(
            endpoint="satellite_search",
            params={"search": satelite_name},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_METADATA"],
            source="DB",
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?search={p['search']}",
        )
        if isinstance(data, list):
            data.sort(
                key=lambda s: s.get("name", "").lower() != satelite_name.lower()
            )
            data = paginate(data, limit, offset)
        return build_response(data, source, cache_age)
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
            url_builder=lambda p: f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/?sat_id={p['sat_id']}",
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
@async_lru_cache(maxsize=128)
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
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/telemetry/?satellite={p['satellite']}",
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