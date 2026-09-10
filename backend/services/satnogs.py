import time
import httpx
from typing import Any, Optional, Callable
from utils.config import SATNOGS_CONFIG, RESILIENCE_CONFIG
from utils.cache import cache_manager


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self) -> None:
        self.failure_count = 0
        self.state = "closed"

    def on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def is_open(self) -> bool:
        return self.state == "open"


circuit_breakers = {
    "DB": CircuitBreaker(
        failure_threshold=RESILIENCE_CONFIG["CIRCUIT_FAILURE_THRESHOLD"],
        recovery_timeout=RESILIENCE_CONFIG["CIRCUIT_RECOVERY_TIMEOUT"],
    ),
    "NETWORK": CircuitBreaker(
        failure_threshold=RESILIENCE_CONFIG["CIRCUIT_FAILURE_THRESHOLD"],
        recovery_timeout=RESILIENCE_CONFIG["CIRCUIT_RECOVERY_TIMEOUT"],
    ),
}

HEADERS = {
    "DB": {
        "Accept": "application/json",
        "Authorization": f"TOKEN {SATNOGS_CONFIG['DB_TOKEN_SATNOGS']}",
    },
    "NETWORK": {
        "Accept": "application/json",
        "Authorization": f"TOKEN {SATNOGS_CONFIG['NETWORK_TOKEN']}",
    },
}


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    source: str,
) -> httpx.Response:
    max_attempts = RESILIENCE_CONFIG["RETRY_MAX_ATTEMPTS"]
    backoff_factor = RESILIENCE_CONFIG["RETRY_BACKOFF_FACTOR"]
    backoff_max = RESILIENCE_CONFIG["RETRY_BACKOFF_MAX"]
    timeout = RESILIENCE_CONFIG["REQUEST_TIMEOUT"]

    last_exception = None
    for attempt in range(max_attempts):
        try:
            response = await client.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as e:
            last_exception = e
            if attempt < max_attempts - 1:
                wait_time = min(backoff_factor * (2**attempt), backoff_max)
                time.sleep(wait_time)
            continue

    raise last_exception


async def fetch_with_cache(
    endpoint: str,
    params: dict,
    ttl: int,
    source: str,
    url_builder: Callable[[dict], str],
) -> tuple[Any, str, int]:
    cached_data, cache_status, cache_age = cache_manager.get(endpoint, params, ttl)

    if cached_data is not None and cache_status == "cache":
        return cached_data, "cache", cache_age

    cb = circuit_breakers[source]
    if cb.is_open():
        if cached_data is not None:
            return cached_data, "stale", cache_age or 0
        raise Exception(f"Circuit breaker open for {source} and no cached data available")

    async with httpx.AsyncClient() as client:
        try:
            url = url_builder(params)
            response = await cb.call(
                fetch_with_retry,
                client,
                url,
                HEADERS[source],
                source,
            )
            data = response.json()
            cache_manager.set(endpoint, params, data)
            return data, "live", 0
        except Exception as e:
            if cached_data is not None:
                return cached_data, "stale", cache_age or 0
            raise e