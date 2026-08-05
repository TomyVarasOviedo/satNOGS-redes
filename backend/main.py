from utils.config import SATNOGS_CONFIG, SERVER_CONFIG

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from requests.exceptions import HTTPError
import uvicorn


app = FastAPI()
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
        satelite_info = requests.get(
                f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?sat_id={satelite_id}",
                headers=HEADERS["DB"]
            )
        satelite_info.raise_for_status()
        return {
            "status": satelite_info.status_code, 
            "data": satelite_info.json()
        }
    
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": satelite_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

@app.get("/satelites/{satelite_name}")
async def get_satelite_by_name(satelite_name: str):
    """
    Get satellite information by its name.

    @param satelite_name: The name of the satellite for which to retrieve information.
    @return: A dictionary containing the status code and satellite information, or an error message.
    """
    try:
        satelite_info = requests.get(
                f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites?search={satelite_name}",
                headers=HEADERS["DB"]
            )
        satelite_info.raise_for_status()
        return {
            "status": satelite_info.status_code, "data": satelite_info.json()}
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": satelite_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

@app.get("/observations/{satelite_id}")
async def get_observations_by_satelite_id(satelite_id: str):
    """
    Get observation data for a specific satellite by its ID.

    @param satelite_id: The ID of the satellite for which to retrieve observation data.
    @return: A dictionary containing the status code and observation data, or an error message.
    """
    try:
        observations_info = requests.get(
                f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/?sat_id={satelite_id}",
                headers=HEADERS["NETWORK"]
            )
        observations_info.raise_for_status()
        return {
            "status": observations_info.status_code, 
            "data": observations_info.json()
        }
    
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
        observations_info = requests.get(
                f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/{id}",
                headers=HEADERS["NETWORK"]
            )
        observations_info.raise_for_status()
        return {
            "status": observations_info.status_code, 
            "data": observations_info.json()
        }
    
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": observations_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

@app.get("/telemetry/{satelite_id}")
async def get_telemetry_by_satelite_id(satelite_id: int):
    """
    .. TODO:: Try and fixed 

    Get telemetry data for a specific satellite by its ID.
    
    @param satelite_id: The ID of the satellite for which to retrieve telemetry data.
    @return: A dictionary containing the status code and telemetry data, or an error message.
    """
    try:
        telemetry_info = requests.get(
                f"{SATNOGS_CONFIG['NETWORK_URL']}/{satelite_id}/telemetry",
                headers=HEADERS["NETWORK"]
            )
        telemetry_info.raise_for_status()
        return {
            "status": telemetry_info.status_code, 
            "data": telemetry_info.json()
        }
    
    except HTTPError as http_err:
        return {
            "error": f"{http_err}", 
            "status_code": telemetry_info.status_code
            }
    except Exception as e:
        return {"error": str(e), "status_code": 500}

if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_CONFIG['HOST'], port=int(SERVER_CONFIG['PORT']))