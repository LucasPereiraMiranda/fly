from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fly.catalog import Destination


@dataclass(frozen=True)
class Route:
    origin: str
    destination: str

    def reversed(self) -> Route:
        return Route(self.destination, self.origin)


@dataclass(frozen=True)
class Baseline:
    """The route's normal price, against which discounts are measured."""

    value: float
    unit: Literal["miles", "brl"]
    estimated: bool


@dataclass(frozen=True)
class SourceState:
    """Health of a price source: whether it may be queried and how it has been failing."""

    name: str
    status: Literal["ok", "paused"]
    paused_until: datetime | None
    backoff_minutes: int
    failure_streak: int
    last_error: str | None
    notified: bool


@dataclass(frozen=True)
class FeedItem:
    """One post from a promo site's RSS feed."""

    feed: str
    url: str
    title: str
    summary: str
    categories: tuple[str, ...]
    published_at: datetime


@dataclass(frozen=True)
class PriceLine:
    """A price row found in an article (e.g. one line of a fares table)."""

    origin: str
    destination: str
    airline: str
    program: str | None
    miles: int | None
    cash_brl: Decimal | None
    dates: tuple[date, ...]
    per_segment: bool | None  # None: the article does not say per segment or round trip


@dataclass(frozen=True)
class Article:
    url: str
    text: str
    bh_mentioned: bool
    bh_prices: tuple[PriceLine, ...]
    dates: tuple[date, ...]
    expired: bool


@dataclass(frozen=True)
class PostDecision:
    item: FeedItem
    tier: Literal["alert", "digest", "drop"]
    reason: str
    destination: Destination | None
    price: PriceLine | None
    baseline: Baseline | None
    discount: float | None
