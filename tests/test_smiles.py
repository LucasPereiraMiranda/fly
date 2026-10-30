from datetime import date

import pytest

from conftest import T0
from fly.models import Route
from fly.sources.base import SourceBlocked, SourceNetworkError
from fly.sources.smiles import SmilesSource, build_search_url

ROUTE = Route("CNF", "MCZ")


class FakeSession:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def fetch_json(self, url, match, timeout_ms=30000):
        self.calls.append((url, match))
        if self.error:
            raise self.error
        return self.result


def test_build_search_url():
    u = build_search_url(ROUTE, date(2026, 12, 10))
    assert u.startswith("https://www.smiles.com.br/mfe/emissao-passagem/?")
    assert "departureDate=1796904000000" in u
    assert "originAirport=CNF" in u and "destinationAirport=MCZ" in u
    assert "adults=1" in u and "tripType=2" in u


@pytest.mark.parametrize("status", [403, 406])
def test_blocked_status_raises(status):
    src = SmilesSource(FakeSession(result=(status, None)), lambda: T0)
    with pytest.raises(SourceBlocked):
        src.fetch_week(ROUTE, date(2026, 12, 10))


def test_fetch_listens_for_carousel():
    session = FakeSession(result=(403, None))
    with pytest.raises(SourceBlocked):
        SmilesSource(session, lambda: T0).fetch_week(ROUTE, date(2026, 12, 10))
    assert session.calls == [(build_search_url(ROUTE, date(2026, 12, 10)), "carousel/pricing")]


def test_network_failure_raises_network_error():
    src = SmilesSource(FakeSession(error=SourceNetworkError("offline")), lambda: T0)
    with pytest.raises(SourceNetworkError):
        src.fetch_week(ROUTE, date(2026, 12, 10))
