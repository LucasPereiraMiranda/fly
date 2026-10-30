from fly.baseline import load_seeds, normal_for
from fly.models import Baseline, Route


def test_seed_midpoint_when_no_history():
    assert normal_for((30000, 40000), [], scan_days=0) == Baseline(35000, "miles", True)


def test_history_median_beats_seed():
    lows = [30000.0] * 10 + [36000.0] * 11 + [8000.0]  # 8000 dropped (< 17500)
    assert normal_for((30000, 40000), lows, scan_days=10) == Baseline(36000, "miles", False)


def test_history_estimated_when_few_scan_days():
    assert normal_for(None, [20000.0] * 30, scan_days=3) == Baseline(20000, "miles", True)


def test_no_seed_no_history_none():
    assert normal_for(None, [20000.0] * 5, scan_days=1) is None


def test_load_seeds_has_maceio():
    assert load_seeds()[("smiles", Route("CNF", "MCZ"))] == (30000, 40000)
