from __future__ import annotations

from datetime import date
from typing import Protocol

from fly.models import FareQuote, Route


class SourceError(Exception):
    """The source answered something we could not use (e.g. the page format changed)."""


class SourceBlocked(SourceError):
    """The site refused us (anti-bot block). The source must back off."""


class SourceNetworkError(SourceError):
    """Our own connectivity failed (offline, DNS, asleep). Not the site's fault."""


class Source(Protocol):
    name: str

    def fetch_week(self, route: Route, center: date) -> list[FareQuote]:
        """Lowest prices for the days around `center`."""
        ...

    def link(self, route: Route, day: date) -> str:
        """Public page where the traveler can see and book this flight."""
        ...
