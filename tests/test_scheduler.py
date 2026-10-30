from datetime import date, timedelta

from conftest import T0
from fly.catalog import Destination
from fly.models import Route
from fly.scheduler import plan_round

REVISIT = {"alta": 2, "media": 5, "baixa": 14}
MCZ = Destination("MCZ", "Maceio", "nordeste", "alta", "BR")
LIS = Destination("LIS", "Lisboa", "europa", "baixa", "PT")


def test_plan_round_budget_and_priority():
    items = plan_round("smiles", [LIS, MCZ], "CNF", date(2026, 10, 29), (60, 240), REVISIT,
                       lambda *a: None, T0, budget=10)
    assert len(items) == 10 and items[0].route == Route("CNF", "MCZ")
    assert items[0].week_start == date(2026, 12, 28) and items[0].center == date(2026, 12, 31)
    assert items[1].route == Route("MCZ", "CNF")


def test_plan_round_skips_recent():
    items = plan_round("smiles", [MCZ], "CNF", date(2026, 10, 29), (60, 74), {"alta": 2},
                       lambda *a: T0 - timedelta(days=1), T0, budget=10)
    assert items == []


def test_plan_round_most_overdue_first():
    def last(source, route, week):
        # LIS (revisit 14d) scanned 28 days ago = 2x overdue; MCZ (revisit 2d) 3 days ago = 1.5x
        return T0 - timedelta(days=28 if route.destination == "LIS" or route.origin == "LIS" else 3)

    items = plan_round("smiles", [MCZ, LIS], "CNF", date(2026, 10, 29), (60, 66), REVISIT, last, T0, budget=1)
    assert items[0].route.destination == "LIS"
