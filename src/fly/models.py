from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal


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


@dataclass(frozen=True)
class Baseline:
    """The route's normal price, against which discounts are measured."""

    value: float
    unit: Literal["miles", "brl"]
    estimated: bool


@dataclass(frozen=True)
class Deal:
    quote: FareQuote
    baseline: Baseline
    discount: float
    tier: Literal["alert", "digest"]
