from datetime import date
from decimal import Decimal

from conftest import quote
from fly.models import Route
from fly.trip import best_return


def test_best_return_window():
    out = quote(flight_date=date(2026, 11, 11), miles=8000)

    def back(d, m):
        return quote(route=Route("MCZ", "CNF"), flight_date=d, miles=m)

    cands = [
        back(date(2026, 11, 12), 5000),  # 1 day later: too soon
        back(date(2026, 11, 27), 18000),
        back(date(2026, 11, 20), 25000),
        back(date(2026, 12, 15), 4000),  # 34 days later: too late
    ]
    assert best_return(out, cands, {"smiles": Decimal("16.84")}).flight_date == date(2026, 11, 27)


def test_best_return_ignores_other_routes():
    out = quote(flight_date=date(2026, 11, 11), miles=8000)
    other = quote(route=Route("REC", "CNF"), flight_date=date(2026, 11, 20), miles=1000)
    assert best_return(out, [other], {"smiles": Decimal("16.84")}) is None
