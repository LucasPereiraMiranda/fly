from conftest import quote
from fly.detect import classify, dedupe_key, should_alert
from fly.models import Baseline

NORMAL = Baseline(35000, "miles", False)


def test_maceio_8k_is_alert():
    d = classify(quote(miles=8000), NORMAL)
    assert d.tier == "alert" and round(d.discount, 3) == 0.771


def test_digest_band():
    assert classify(quote(miles=21000), NORMAL).tier == "digest"  # 40%


def test_small_discount_ignored():
    assert classify(quote(miles=30000), NORMAL) is None


def test_zero_or_missing_miles_never_deal():
    assert classify(quote(miles=0), NORMAL) is None
    assert classify(quote(miles=None), NORMAL) is None


def test_dedupe_and_realert():
    assert dedupe_key(quote()) == "smiles:CNF-MCZ:2026-12-10"
    assert should_alert(8000, None)
    assert not should_alert(7500, 8000)
    assert should_alert(7200, 8000)
