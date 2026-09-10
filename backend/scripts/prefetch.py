#!/usr/bin/env python3
"""
Script de precarga de caché para el backend.
Ejecutar con buena conectividad a internet para poblar la caché local.
La carpeta de caché (CACHE_DIR) puede copiarse luego al equipo con conectividad limitada.
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import RESILIENCE_CONFIG, SATELLITES_TO_MONITOR, SATNOGS_CONFIG
from utils.cache import cache_manager
from services.satnogs import fetch_with_cache, circuit_breakers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def get_sat_id(norad_id: int) -> str | None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=RESILIENCE_CONFIG["REQUEST_TIMEOUT"]) as client:
            response = await client.get(
                f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?norad_cat_id={norad_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"TOKEN {SATNOGS_CONFIG['DB_TOKEN_SATNOGS']}",
                },
            )
            response.raise_for_status()
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get("sat_id")
    except Exception as e:
        logger.error(f"Error getting sat_id for NORAD {norad_id}: {e}")
    return None


async def prefetch_satellite(sat_id: str, name: str) -> None:
    logger.info(f"Prefetching {name} (sat_id: {sat_id})")

    try:
        await fetch_with_cache(
            endpoint="satellite_metadata",
            params={"sat_id": sat_id},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_METADATA"],
            source="DB",
            url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?sat_id={p['sat_id']}",
        )
        logger.info(f"  Metadata cached for {name}")
    except Exception as e:
        logger.error(f"  Failed to prefetch metadata for {name}: {e}")

    try:
        await fetch_with_cache(
            endpoint="observations",
            params={"sat_id": sat_id},
            ttl=RESILIENCE_CONFIG["DEFAULT_TTL_OBSERVATIONS"],
            source="NETWORK",
            url_builder=lambda p: f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/?sat_id={p['sat_id']}",
        )
        logger.info(f"  Observations cached for {name}")
    except Exception as e:
        logger.error(f"  Failed to prefetch observations for {name}: {e}")


async def main() -> None:
    logger.info("Starting cache prefetch...")
    logger.info(f"Cache directory: {RESILIENCE_CONFIG['CACHE_DIR']}")
    logger.info(f"Satellites to monitor: {len(SATELLITES_TO_MONITOR)}")

    for sat in SATELLITES_TO_MONITOR:
        norad_id = sat["norad_id"]
        name = sat["name"]

        logger.info(f"\nProcessing {name} (NORAD: {norad_id})...")

        sat_id = await get_sat_id(norad_id)
        if not sat_id:
            logger.warning(f"  Could not find sat_id for NORAD {norad_id}, skipping")
            continue

        await prefetch_satellite(sat_id, name)

    logger.info("\nCache prefetch completed!")
    logger.info(f"Cache files stored in: {RESILIENCE_CONFIG['CACHE_DIR']}")


if __name__ == "__main__":
    asyncio.run(main())