import httpx
import pytest

from api import ApiError, NocApi


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
