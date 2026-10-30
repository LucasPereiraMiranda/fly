from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timezone
from urllib.parse import urlencode

from fly.models import FareQuote, Route
from fly.sources.base import SourceBlocked, SourceError

SEARCH_PAGE = "https://www.smiles.com.br/mfe/emissao-passagem/"
CAROUSEL_MATCH = "carousel/pricing"
BLOCKED_STATUSES = (403, 406)


def build_search_url(route: Route, day: date) -> str:
    """Public one-way search page (no login), as the site built it on 2026-10-29."""
    departure_ms = int(datetime.combine(day, time(12), tzinfo=timezone.utc).timestamp() * 1000)
    params = {
        "adults": 1, "cabin": "ALL", "children": 0, "departureDate": departure_ms, "infants": 0,
        "isElegible": "false", "isFlexibleDateChecked": "false", "returnDate": "",
        "searchType": "g3", "segments": 1, "tripType": 2,
        "originAirport": route.origin, "originCity": "", "originCountry": "",
        "originAirportIsAny": "false",
        "destinationAirport": route.destination, "destinCity": "", "destinCountry": "",
        "destinAirportIsAny": "false", "novo-resultado-voos": "true",
    }
    return f"{SEARCH_PAGE}?{urlencode(params)}"


def parse_carousel(payload: dict, route: Route, observed_at: datetime) -> list[FareQuote]:
    raise NotImplementedError("written against the captured fixture (plan Task 8, Step 5)")


class SmilesSource:
    name = "smiles"

    def __init__(self, session, clock: Callable[[], datetime]) -> None:
        self._session = session
        self._clock = clock

    def link(self, route: Route, day: date) -> str:
        return build_search_url(route, day)

    def fetch_week(self, route: Route, center: date) -> list[FareQuote]:
        status, payload = self._session.fetch_json(build_search_url(route, center), CAROUSEL_MATCH)
        if status in BLOCKED_STATUSES:
            raise SourceBlocked(f"HTTP {status}")
        if status != 200 or payload is None:
            raise SourceError(f"no carousel response (HTTP {status})")
        try:
            return parse_carousel(payload, route, self._clock())
        except ValueError as exc:
            raise SourceError(f"carousel format: {exc}") from exc
