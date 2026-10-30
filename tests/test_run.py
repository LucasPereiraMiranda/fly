from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from conftest import T0, quote
from fly.catalog import Destination
from fly.config import load_settings
from fly.models import Route
from fly.run import build_digest, run_round
from fly.sources.base import SourceBlocked, SourceError, SourceNetworkError

OUT = Route("CNF", "MCZ")
BACK = Route("MCZ", "CNF")
CATALOG = [Destination("MCZ", "Maceió", "nordeste", "alta", "BR")]
SEEDS = {("smiles", OUT): (30000, 40000)}
PROMO_DAY = date(2026, 11, 11)


class FakeSource:
    name = "smiles"

    def __init__(self, responses):
        """responses: route -> list of (list[FareQuote] | Exception); the last one repeats."""
        self.responses, self.calls = responses, []

    def fetch_week(self, route, center):
        self.calls.append((route, center))
        seq = self.responses.get(route, [[]])
        result = seq[min(sum(1 for r, _ in self.calls if r == route) - 1, len(seq) - 1)]
        if isinstance(result, Exception):
            raise result
        return result

    def link(self, route, day):
        return f"https://example.test/{route.origin}-{route.destination}/{day}"


class FakeNotifier:
    def __init__(self, ok=True):
        self.ok, self.sent = ok, []

    def send(self, text):
        self.sent.append(text)
        return self.ok


@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(Path("config/fly.toml"), tmp_path / "none.env"), smiles_budget_per_round=1)


def _round(db, source, notifier, settings, now=T0):
    return run_round(db=db, sources={"smiles": source}, notifier=notifier, catalog=CATALOG,
                     seeds=SEEDS, settings=settings, now=now, sleep=lambda s: None)


def test_maceio_promo_alerts_once(db, settings):
    db.add_quotes([quote(route=BACK, flight_date=date(2026, 11, 27), miles=18000)])
    src = FakeSource({OUT: [[quote(flight_date=PROMO_DAY, miles=8000)]]})
    notifier = FakeNotifier()
    report = _round(db, src, notifier, settings)
    assert report.alerts_sent == 1 and len(notifier.sent) == 1
    assert "77% abaixo" in notifier.sent[0] and "27/11/2026" in notifier.sent[0]
    _round(db, src, notifier, settings)
    assert len(notifier.sent) == 1


def test_reconfirm_drops_vanished_promo(db, settings):
    src = FakeSource({OUT: [[quote(flight_date=PROMO_DAY, miles=8000)], [quote(flight_date=PROMO_DAY, miles=36000)]]})
    notifier = FakeNotifier()
    _round(db, src, notifier, settings)
    assert notifier.sent == [] and len(src.calls) == 2


def test_failed_send_not_recorded(db, settings):
    src = FakeSource({OUT: [[quote(flight_date=PROMO_DAY, miles=8000)]]})
    _round(db, src, FakeNotifier(ok=False), settings)
    assert db.last_alert_value(f"smiles:CNF-MCZ:{PROMO_DAY}") is None
    notifier = FakeNotifier()
    _round(db, src, notifier, settings)
    assert len(notifier.sent) == 1


def test_out_of_window_not_alerted(db, settings):
    soon = T0.date() + timedelta(days=30)
    src = FakeSource({OUT: [[quote(flight_date=soon, miles=8000)]]})
    notifier = FakeNotifier()
    _round(db, src, notifier, settings)
    assert notifier.sent == []
    assert db.latest_quotes("smiles", OUT, T0)[0].flight_date == soon


def test_blocked_pauses_source(db, settings):
    src = FakeSource({OUT: [SourceBlocked("HTTP 403")]})
    _round(db, src, FakeNotifier(), replace(settings, smiles_budget_per_round=5))
    assert db.get_state("smiles").status == "paused" and len(src.calls) == 1


def test_paused_source_skipped(db, settings):
    src = FakeSource({OUT: [SourceBlocked("HTTP 403")]})
    _round(db, src, FakeNotifier(), settings)
    report = _round(db, src, FakeNotifier(), settings, now=T0 + timedelta(minutes=5))
    assert report.skipped_sources == ["smiles"] and len(src.calls) == 1


def test_network_error_no_pause(db, settings):
    src = FakeSource({OUT: [SourceNetworkError("offline")]})
    _round(db, src, FakeNotifier(), settings)
    state = db.get_state("smiles")
    assert state.status == "ok" and state.failure_streak == 1


def test_health_notice_after_three_errors(db, settings):
    src = FakeSource({OUT: [SourceError("format")]})
    notifier = FakeNotifier()
    for _ in range(4):
        _round(db, src, notifier, settings)
    assert [t for t in notifier.sent if t.startswith("⚠️")] == [
        "⚠️ fly: fonte smiles com problema (format) — 3 falhas seguidas."
    ]


def test_digest_lists_band(db, settings):
    db.add_quotes([quote(flight_date=PROMO_DAY, miles=21000, observed_at=T0 - timedelta(hours=2))])
    text = build_digest(db=db, catalog=CATALOG, seeds=SEEDS, settings=settings, now=T0)
    assert "(-40%)" in text


def test_digest_empty(db, settings):
    text = build_digest(db=db, catalog=CATALOG, seeds=SEEDS, settings=settings, now=T0)
    assert "Nada entre 30% e 50% abaixo do normal hoje" in text
