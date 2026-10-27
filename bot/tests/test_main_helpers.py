import pytest

from api import AmbiguousSatellite, SatelliteNotFound
from main import _resolve_name_and_days


class FakeApi:
    def __init__(self, known=None, partial=None, ambiguous=()):
        self.known = known or {}
        self.partial = partial or {}
        self.ambiguous = set(ambiguous)

    async def resolve_sat_id(self, name: str, exact_only: bool = False) -> str:
        if name in self.ambiguous:
            raise AmbiguousSatellite(f"El nombre '{name}' devuelve más de un satélite")
        if name in self.known:
            return self.known[name]
        if not exact_only and name in self.partial:
            return self.partial[name]
        raise SatelliteNotFound(f"No se encontró el satélite '{name}'")


@pytest.mark.asyncio
async def test_full_name_with_number_wins_over_days():
    api = FakeApi({"NOAA 18": "SWSC"})

    assert await _resolve_name_and_days(api, ["NOAA", "18"]) == ("NOAA 18", None)


@pytest.mark.asyncio
async def test_partial_full_name_with_number_falls_back_to_days():
    api = FakeApi({"LUSAT": "ZDPY"}, partial={"LUSAT 3": "OTRO"})

    assert await _resolve_name_and_days(api, ["LUSAT", "3"]) == ("LUSAT", 3)


@pytest.mark.asyncio
async def test_trailing_digit_is_days_when_full_name_does_not_exist():
    api = FakeApi({"LUSAT": "ZDPY"})

    assert await _resolve_name_and_days(api, ["LUSAT", "3"]) == ("LUSAT", 3)


@pytest.mark.asyncio
async def test_only_a_digit_means_days_without_name():
    api = FakeApi()

    assert await _resolve_name_and_days(api, ["3"]) == (None, 3)


@pytest.mark.asyncio
async def test_ambiguous_full_name_is_not_split():
    api = FakeApi(ambiguous={"x 3"})

    with pytest.raises(AmbiguousSatellite):
        await _resolve_name_and_days(api, ["x", "3"])


@pytest.mark.asyncio
async def test_plain_name_is_returned_unchanged():
    api = FakeApi()

    assert await _resolve_name_and_days(api, ["NOAA", "18", "x"]) == ("NOAA 18 x", None)
    assert await _resolve_name_and_days(api, []) == (None, None)
