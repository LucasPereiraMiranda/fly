from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from conftest import T0, quote
from fly.db import Database
from fly.models import Route


def test_daily_lows_takes_min_per_date(db):
    db.add_quotes([quote(miles=30000), quote(miles=28000), quote(flight_date=date(2026, 12, 11), miles=40000)])
    assert sorted(db.daily_lows("smiles", Route("CNF", "MCZ"), T0)) == [28000.0, 40000.0]


def test_daily_lows_respects_since(db):
    db.add_quotes([quote(miles=20000, observed_at=T0 - timedelta(days=90)), quote(miles=30000)])
    assert db.daily_lows("smiles", Route("CNF", "MCZ"), T0 - timedelta(days=60)) == [30000.0]


def test_scan_days_counts_distinct_days(db):
    db.add_quotes([quote(), quote(observed_at=T0 + timedelta(hours=3)), quote(observed_at=T0 + timedelta(days=1))])
    assert db.scan_days("smiles", Route("CNF", "MCZ"), T0) == 2


def test_latest_quotes_one_per_date_roundtrip(db):
    db.add_quotes([
        quote(miles=30000, taxes_brl=Decimal("49.90")),
        quote(miles=25000, taxes_brl=Decimal("49.90"), observed_at=T0 + timedelta(hours=1)),
    ])
    [latest] = db.latest_quotes("smiles", Route("CNF", "MCZ"), T0)
    assert latest == quote(miles=25000, taxes_brl=Decimal("49.90"), observed_at=T0 + timedelta(hours=1))


def test_alert_roundtrip(db):
    assert db.last_alert_value("k") is None
    db.record_alert("k", 8000, T0)
    assert db.last_alert_value("k") == 8000


def test_state_default_and_save(db):
    s = db.get_state("smiles")
    assert s.status == "ok" and s.failure_streak == 0 and s.paused_until is None
    db.save_state(replace(s, failure_streak=2, status="paused", paused_until=T0))
    got = db.get_state("smiles")
    assert got.failure_streak == 2 and got.status == "paused" and got.paused_until == T0


def test_scan_cursor(db):
    r = Route("CNF", "MCZ")
    w = date(2027, 1, 4)
    assert db.last_scanned("smiles", r, w) is None
    db.mark_scanned("smiles", r, w, T0)
    assert db.last_scanned("smiles", r, w) == T0


def test_init_idempotent(tmp_path):
    d = Database(tmp_path / "t.db")
    d.init()
    d.init()
