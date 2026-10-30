from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Route:
    origin: str
    destination: str

    def reversed(self) -> Route:
        return Route(self.destination, self.origin)


@dataclass(frozen=True)
class FareQuote:
    source: str
    route: Route
    flight_date: date
    miles: int | None
    cash_brl: Decimal | None
    taxes_brl: Decimal | None
    observed_at: datetime
