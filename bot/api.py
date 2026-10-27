from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx


class ApiError(Exception):
    """Error de red o de la API del backend."""


@dataclass(frozen=True)
class ApiResult:
    data: Any
    source: str
    cache_age: int


def _iso(value: str | datetime) -> str:
    if isinstance(value, str):
        return value
    moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _name_matches(satellite: dict, name: str) -> bool:
    term = name.strip().lower()
    candidates = [satellite.get("name") or ""] + (satellite.get("names") or "").split(",")
    return any(term == candidate.strip().lower() for candidate in candidates)


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()[:200]
    if isinstance(payload, dict):
        for key in ("error", "detail", "message"):
            if payload.get(key):
                return str(payload[key])
    return ""


class NocApi:
    """Cliente mínimo de la API del backend; no importa nada de backend/."""

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 20,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client
        self._owns_client = client is None
        self.timeout = timeout
        self._sat_ids: dict[str, str] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(self, path: str, params: dict | None = None) -> ApiResult:
        client = await self._get_client()
        try:
            response = await client.get(f"{self.base_url}{path}", params=params)
        except httpx.HTTPError as exc:
            raise ApiError(f"No se pudo contactar el backend: {exc}") from exc

        source = response.headers.get("X-Source", "unknown")
        try:
            cache_age = int(response.headers.get("X-Cache-Age", "0") or 0)
        except ValueError:
            cache_age = 0

        if response.status_code >= 400:
            raise ApiError(_detail(response) or f"El backend respondió {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiError("El backend devolvió una respuesta inválida") from exc
        return ApiResult(data=data, source=source, cache_age=cache_age)

    async def monitored(self) -> ApiResult:
        return await self._get("/satellites/monitored")

    async def resolve_sat_id(self, name: str) -> str:
        key = name.strip().lower()
        if key in self._sat_ids:
            return self._sat_ids[key]

        result = await self._get(f"/satelites/{quote(name.strip(), safe='')}")
        matches = result.data if isinstance(result.data, list) else []
        if not matches:
            raise ApiError(f"No se encontró el satélite '{name}'")

        chosen = next((sat for sat in matches if _name_matches(sat, name)), matches[0])
        sat_id = chosen.get("sat_id")
        if not sat_id:
            raise ApiError(f"El satélite '{name}' no tiene sat_id en la respuesta")
        self._sat_ids[key] = sat_id
        return sat_id

    async def passes(
        self,
        sat_id: str,
        days: float = 2,
        horizon_deg: float | None = None,
        start: str | datetime | None = None,
    ) -> ApiResult:
        params: dict[str, Any] = {"sat_id": sat_id, "days": days}
        if horizon_deg is not None:
            params["horizon_deg"] = horizon_deg
        if start is not None:
            params["start"] = _iso(start)
        return await self._get("/predictions/passes", params)

    async def doppler(
        self,
        sat_id: str,
        start: str | datetime | None = None,
        horizon_deg: float | None = None,
    ) -> ApiResult:
        params: dict[str, Any] = {"sat_id": sat_id}
        if start is not None:
            params["start"] = _iso(start)
        if horizon_deg is not None:
            params["horizon_deg"] = horizon_deg
        return await self._get("/predictions/doppler", params)

    async def orbit(self, sat_id: str) -> ApiResult:
        return await self._get("/orbits/classify", {"sat_id": sat_id})
