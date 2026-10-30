from dataclasses import replace
from datetime import date, datetime

from fly.models import FareQuote, Route

T0 = datetime(2026, 9, 1, 10, 0)

_DEFAULT = FareQuote(
    source="smiles",
    route=Route("CNF", "MCZ"),
    flight_date=date(2026, 12, 10),
    miles=30000,
    cash_brl=None,
    taxes_brl=None,
    observed_at=T0,
)


def quote(**overrides) -> FareQuote:
    return replace(_DEFAULT, **overrides)
