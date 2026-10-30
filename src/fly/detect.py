from __future__ import annotations

from typing import Literal

from fly.models import Baseline


def discount_tier(
    price: float,
    baseline: Baseline,
    alert_at: float,
    digest_at: float,
) -> tuple[float, Literal["alert", "digest"] | None]:
    """How far below normal a price is, and whether that earns an alert or a digest line."""
    if price <= 0 or baseline.value <= 0:
        return 0.0, None
    discount = 1 - price / baseline.value
    if discount >= alert_at:
        return discount, "alert"
    if discount >= digest_at:
        return discount, "digest"
    return discount, None
