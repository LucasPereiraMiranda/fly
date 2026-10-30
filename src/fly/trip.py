from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import timedelta
from decimal import Decimal

from fly.models import FareQuote
from fly.money import brl_equivalent


def best_return(
    outbound: FareQuote,
    candidates: Iterable[FareQuote],
    milheiro_brl: Mapping[str, Decimal],
    min_days: int = 2,
    max_days: int = 30,
) -> FareQuote | None:
    """Cheapest return flight (in BRL equivalent) within the trip-length window."""
    back = outbound.route.reversed()
    earliest = outbound.flight_date + timedelta(days=min_days)
    latest = outbound.flight_date + timedelta(days=max_days)
    priced = [
        (brl, q)
        for q in candidates
        if q.route == back and earliest <= q.flight_date <= latest
        and (brl := brl_equivalent(q, milheiro_brl)) is not None
    ]
    if not priced:
        return None
    return min(priced, key=lambda pair: pair[0])[1]
