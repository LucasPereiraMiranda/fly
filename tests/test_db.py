from dataclasses import replace
from datetime import datetime, timedelta

from conftest import item

from fly.models import Baseline, PostDecision

NOW = datetime(2026, 10, 29, 10, 0)


def decision(url, tier="alert", published=NOW, discount=None, title="Post"):
    it = replace(item(title, published_at=published), url=url)
    return PostDecision(it, tier, "promoção", None, None, Baseline(60000, "miles", True), discount)


def test_post_seen_roundtrip(db):
    assert not db.post_seen("u1")
    db.record_post(decision("u1"), "msg", None, NOW)
    assert db.post_seen("u1")


def test_pending_alerts_only_unsent_recent(db):
    db.record_post(decision("sent"), "m-sent", None, NOW)
    db.mark_sent("sent")
    db.record_post(decision("old", published=NOW - timedelta(hours=30)), "m-old", None, NOW)
    db.record_post(decision("new"), "m-new", None, NOW)
    db.record_post(decision("dig", tier="digest"), None, "line", NOW)
    assert db.pending_alerts(NOW, 24) == [("new", "m-new")]


def test_digest_lines_order(db):
    db.record_post(decision("a", tier="digest", published=NOW - timedelta(hours=3)), None, "no-discount-older", NOW)
    db.record_post(decision("b", tier="digest", published=NOW - timedelta(hours=1)), None, "no-discount-newer", NOW)
    db.record_post(decision("c", tier="digest", discount=0.35), None, "d35", NOW)
    db.record_post(decision("d", tier="digest", discount=0.45), None, "d45", NOW)
    db.record_post(decision("e", tier="digest", discount=0.40), None, "stale", NOW - timedelta(days=2))
    assert db.digest_lines(NOW - timedelta(hours=24)) == ["d45", "d35", "no-discount-newer", "no-discount-older"]


def test_lowest_seen(db):
    assert db.lowest_seen("smiles", "MVD") is None
    db.add_price_seen("smiles", "MVD", 48000, NOW)
    db.add_price_seen("smiles", "MVD", 28000, NOW)
    db.add_price_seen("azul", "MVD", 10000, NOW)
    assert db.lowest_seen("smiles", "MVD") == 28000


def test_state_default_and_save(db):
    s = db.get_state("pontospravoar")
    assert s.status == "ok" and s.failure_streak == 0
    db.save_state(replace(s, failure_streak=2))
    assert db.get_state("pontospravoar").failure_streak == 2


def test_init_idempotent(db):
    db.init()
    db.init()
