from dotenv import load_dotenv
import os

load_dotenv()

SATNOGS_CONFIG = {
    "NETWORK_TOKEN": os.getenv("NETWORK_TOKEN_SATNOGS"),
    "NETWORK_URL": os.getenv("NETWORK_URL_SATNOGS"),
    "DB_TOKEN_SATNOGS": os.getenv("DB_TOKEN_SATNOGS"),
    "DB_URL_SATNOGS": os.getenv("DB_URL_SATNOGS"),
}

SERVER_CONFIG = {
    "PORT": os.getenv("BACKEND_PORT"),
    "HOST": os.getenv("BACKEND_HOST"),
}