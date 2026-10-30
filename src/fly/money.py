from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from fly.models import FareQuote


def brl_equivalent(quote: FareQuote, milheiro_brl: Mapping[str, Decimal]) -> Decimal | None:
    """Price in BRL: cash as-is, miles valued at the program's price per 1000 plus taxes."""
    if quote.cash_brl is not None:
        return quote.cash_brl
    if quote.miles is None or quote.source not in milheiro_brl:
        return None
    return quote.miles * milheiro_brl[quote.source] / 1000 + (quote.taxes_brl or 0)
