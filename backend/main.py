from utils.config import SATNOGS_CONFIG, SERVER_CONFIG

from functools import wraps
from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import requests
from requests.exceptions import HTTPError
import httpx 
import uvicorn
import json


app = FastAPI()
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

HEADERS = {
    "DB":{
        "Accept": "application/json",
        "Authorization": f"TOKEN {SATNOGS_CONFIG['DB_TOKEN_SATNOGS']}"
    },
    "NETWORK":{
        "Accept": "application/json",
        "Authorization": f"TOKEN {SATNOGS_CONFIG['NETWORK_TOKEN']}"
    }
}

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

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/satelite/{satelite_id}")
async def get_satelite_by_id(satelite_id: str):
    """
    Get satellite information by its ID.

    @param satelite_id: The ID of the satellite for which to retrieve information.
    @return: A dictionary containing the status code and satellite information, or an error message.
    """
    try:
        async with httpx.AsyncClient() as client:
            satelite_info = await client.get(
                f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?sat_id={satelite_id}",
                headers=HEADERS["DB"]
            )
            satelite_info.raise_for_status()
            return Response(
                content=satelite_info.content,
                status_code=satelite_info.status_code,
                media_type="application/json"
            )
    
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": satelite_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

@app.get("/satelites/{satelite_name}")
@async_lru_cache(maxsize=128)
async def get_satelite_by_name(
    satelite_name: str,
    limit: int | None = Query(10, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    """
    Get satellite information by its name.

    @param satelite_name: The name of the satellite for which to retrieve information.
    @param limit: Maximum number of results to return.
    @param offset: Number of results to skip from the beginning.
    @return: A dictionary containing the status code and satellite information, or an error message.
    """
    try:
        async with httpx.AsyncClient() as client:
            satelite_info = await client.get(
                f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?search={satelite_name}",
                headers=HEADERS["DB"]
            )
            satelite_info.raise_for_status()
            satelites = satelite_info.json()
            satelites.sort(
                key=lambda s: s.get("name", "").lower() != satelite_name.lower()
            )
            satelites = paginate(satelites, limit, offset)
            return Response(
                content=json.dumps(satelites),
                status_code=satelite_info.status_code,
                media_type="application/json"
            )
            
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": satelite_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

@app.get("/observations/{satelite_id}")
async def get_observations_by_satelite_id(
    satelite_id: str,
    limit: int | None = Query(10, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    """
    Get observation data for a specific satellite by its ID.

    @param satelite_id: The ID of the satellite for which to retrieve observation data.
    @param limit: Maximum number of results to return.
    @param offset: Number of results to skip from the beginning.
    @return: A dictionary containing the status code and observation data, or an error message.
    """
    try:
        async with httpx.AsyncClient() as client:
            observations_info = await client.get(
                f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/?sat_id={satelite_id}",
                headers=HEADERS["NETWORK"]
            )
            observations_info.raise_for_status()
            observations = observations_info.json()
            observations = paginate(observations, limit, offset)
            return Response(
                content=json.dumps(observations),
                status_code=observations_info.status_code,
                media_type="application/json"
            )
    
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": observations_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

@app.get("/observations/id/{id}")
async def get_observations_by_id(id: int):
    """
    Get observation data for a specific observation by its ID.

    @param id: The ID of the observation for which to retrieve data.
    @return: A dictionary containing the status code and observation data, or an error message.
    """
    try:
        async with httpx.AsyncClient() as client:
            observations_info = await client.get(
                f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/{id}/",
                headers=HEADERS["NETWORK"]
            )
            observations_info.raise_for_status()
            return Response(
                content=observations_info.content,
                status_code=observations_info.status_code,
                media_type="application/json"
            )
    
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": observations_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

@app.get("/telemetry/{satelite_id}")
@async_lru_cache(maxsize=128)
async def get_telemetry_by_satelite_id(
    satelite_id: int,
    limit: int | None = Query(10, ge=1, le=100),
    offset: int | None = Query(None, ge=0),
):
    """
    .. TODO:: Try and fixed 

    Get telemetry data for a specific satellite by its ID.
    
    @param satelite_id: The ID of the satellite for which to retrieve telemetry data.
    @param limit: Maximum number of results to return.
    @param offset: Number of results to skip from the beginning.
    @return: A dictionary containing the status code and telemetry data, or an error message.
    """
    try:
        async with httpx.AsyncClient() as client:
            telemetry_info = await client.get(
                f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/telemetry/?satellite={satelite_id}",
                headers=HEADERS["DB"]
            )
            telemetry_info.raise_for_status()
            telemetry = telemetry_info.json()
            telemetry = paginate(telemetry, limit, offset)
            return Response(
                content=json.dumps(telemetry),
                status_code=telemetry_info.status_code,
                media_type="application/json"
            )
    
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": telemetry_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_CONFIG['HOST'], port=int(SERVER_CONFIG['PORT']))

