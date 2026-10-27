import httpx
import pytest

from api import AmbiguousSatellite, ApiError, NocApi, SatelliteNotFound


def response(status: int, body, source: str = "live") -> httpx.Response:
    return httpx.Response(
        status,
        json=body,
        headers={"X-Source": source, "X-Cache-Age": "12"},
    )


@pytest.mark.asyncio
async def test_resolves_a_satellite_by_exact_name():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/satelites/LUSAT")
        return response(200, [{"name": "LUSAT-OSCAR 19", "sat_id": "BAD"}, {"name": "LUSAT", "sat_id": "ZDPY"}])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    assert await api.resolve_sat_id("LUSAT") == "ZDPY"
    await client.aclose()


@pytest.mark.asyncio
async def test_rejects_a_name_that_matches_several_satellites():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/satelites/x")
        return response(
            200,
            [
                {"name": "LES-1", "sat_id": "AMOM"},
                {"name": "PROSPERO", "sat_id": "MDNJ"},
            ],
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    with pytest.raises(AmbiguousSatellite, match="más de un satélite") as exc:
        await api.resolve_sat_id("x")

    assert "LES-1" in str(exc.value)
    assert "PROSPERO" in str(exc.value)
    await client.aclose()


@pytest.mark.asyncio
async def test_accepts_a_unique_partial_match():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/satelites/NOAA")
        return response(200, [{"name": "NOAA 18", "sat_id": "SWSC"}])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    assert await api.resolve_sat_id("NOAA") == "SWSC"
    await client.aclose()


@pytest.mark.asyncio
async def test_rejects_multiple_exact_matches():
    def handler(request: httpx.Request) -> httpx.Response:
        return response(
            200,
            [
                {"name": "ISS", "sat_id": "ONE"},
                {"name": "ISS", "sat_id": "TWO"},
            ],
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    with pytest.raises(AmbiguousSatellite):
        await api.resolve_sat_id("ISS")

    await client.aclose()


@pytest.mark.asyncio
async def test_reports_when_the_satellite_does_not_exist():
    def handler(request: httpx.Request) -> httpx.Response:
        return response(200, [])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    with pytest.raises(SatelliteNotFound, match="No se encontró"):
        await api.resolve_sat_id("NO EXISTE")

    await client.aclose()


@pytest.mark.asyncio
async def test_exact_only_does_not_accept_a_partial_match():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/satelites/x 3")
        return response(200, [{"name": "AOBA-VELOX 3", "sat_id": "NFQJ"}])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    with pytest.raises(SatelliteNotFound):
        await api.resolve_sat_id("x 3", exact_only=True)

    assert await api.resolve_sat_id("x 3") == "NFQJ"

    with pytest.raises(SatelliteNotFound):
        await api.resolve_sat_id("x 3", exact_only=True)

    await client.aclose()


@pytest.mark.asyncio
async def test_passes_returns_the_source_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/predictions/passes")
        assert request.url.params["sat_id"] == "ZDPY"
        return response(200, {"passes": []}, source="cache")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    result = await api.passes("ZDPY", days=2)

    assert result.source == "cache"
    assert result.cache_age == 12
    await client.aclose()


@pytest.mark.asyncio
async def test_backend_errors_become_api_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return response(500, {"error": "SatNOGS caído"}, source="error")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = NocApi("http://backend", client=client)

    with pytest.raises(ApiError, match="SatNOGS caído"):
        await api.orbit("ZDPY")

    await client.aclose()
