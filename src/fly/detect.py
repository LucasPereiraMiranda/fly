from __future__ import annotations

from fly.models import Baseline, Deal, FareQuote

REALERT_RATIO = 0.9


def classify(
    quote: FareQuote,
    baseline: Baseline,
    alert_at: float = 0.50,
    digest_at: float = 0.30,
) -> Deal | None:
    """Deal tier for a quote measured against the route's normal price, or None."""
    if quote.miles is None or quote.miles <= 0 or baseline.value <= 0:
        return None
    discount = 1 - quote.miles / baseline.value
    if discount >= alert_at:
        return Deal(quote, baseline, discount, "alert")
    if discount >= digest_at:
        return Deal(quote, baseline, discount, "digest")
    return None


def dedupe_key(quote: FareQuote) -> str:
    r = quote.route
    return f"{quote.source}:{r.origin}-{r.destination}:{quote.flight_date.isoformat()}"


def should_alert(new_value: float, last_alerted_value: float | None) -> bool:
    """Alert once per flight; alert again only if the price dropped at least 10% more."""
    return last_alerted_value is None or new_value <= REALERT_RATIO * last_alerted_value
