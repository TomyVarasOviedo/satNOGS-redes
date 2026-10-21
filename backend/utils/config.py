from dotenv import load_dotenv
import os

load_dotenv()

SATNOGS_CONFIG = {
    "NETWORK_TOKEN": os.getenv("NETWORK_TOKEN_SATNOGS"),
    "NETWORK_URL": os.getenv("NETWORK_URL_SATNOGS", "https://network.satnogs.org/api"),
    "DB_TOKEN_SATNOGS": os.getenv("DB_TOKEN_SATNOGS"),
    "DB_URL_SATNOGS": os.getenv("DB_URL_SATNOGS", "https://db.satnogs.org/api"),
}

SERVER_CONFIG = {
    "PORT": os.getenv("BACKEND_PORT"),
    "HOST": os.getenv("BACKEND_HOST"),
}

RESILIENCE_CONFIG = {
    "CACHE_DIR": os.getenv("CACHE_DIR", "./cache"),
    "REQUEST_TIMEOUT": int(os.getenv("REQUEST_TIMEOUT", "10")),
    "RETRY_MAX_ATTEMPTS": int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),
    "RETRY_BACKOFF_FACTOR": float(os.getenv("RETRY_BACKOFF_FACTOR", "0.5")),
    "RETRY_BACKOFF_MAX": int(os.getenv("RETRY_BACKOFF_MAX", "30")),
    "CIRCUIT_FAILURE_THRESHOLD": int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "5")),
    "CIRCUIT_RECOVERY_TIMEOUT": int(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "60")),
    "REFRESH_INTERVAL": int(os.getenv("REFRESH_INTERVAL", "300")),
    "DEFAULT_TTL_METADATA": int(os.getenv("DEFAULT_TTL_METADATA", "86400")),
    "DEFAULT_TTL_OBSERVATIONS": int(os.getenv("DEFAULT_TTL_OBSERVATIONS", "300")),
    "DEFAULT_TTL_TELEMETRY": int(os.getenv("DEFAULT_TTL_TELEMETRY", "600")),
    "DEFAULT_TTL_TLE": int(os.getenv("DEFAULT_TTL_TLE", "21600")),
}

REFERENCE_STATION = {
    "name": os.getenv("STATION_NAME", "Universidad de Belgrano"),
    "lat": float(os.getenv("STATION_LAT", "-34.5627")),
    "lng": float(os.getenv("STATION_LNG", "-58.4566")),
    "alt_m": float(os.getenv("STATION_ALT_M", "25")),
    "min_elevation_deg": float(os.getenv("STATION_MIN_ELEVATION_DEG", "10")),
}

SATELLITES_TO_MONITOR = [
    {"norad_id": 25544, "name": "ISS"},
    {"norad_id": 20442, "name": "LUSAT"},
    {"norad_id": 28654, "name": "NOAA 18"},
    {"norad_id": 40069, "name": "METEOR-M2"},
    {"norad_id": 39444, "name": "FUNCUBE-1"},
]