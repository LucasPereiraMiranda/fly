from __future__ import annotations

import tomllib
from collections.abc import Sequence
from pathlib import Path
from statistics import median

from fly.models import Baseline, Route

MIN_FLIGHT_DATES = 21
MIN_SCAN_DAYS = 7


def load_seeds(path: Path = Path("config/seeds.toml")) -> dict[tuple[str, Route], tuple[int, int]]:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return {
        (s["source"], Route(s["origin"], s["destination"])): (s["min"], s["max"])
        for s in raw.get("seed", [])
    }


def normal_for(
    seed: tuple[int, int] | None,
    daily_lows: Sequence[float],
    scan_days: int,
) -> Baseline | None:
    """Normal price in miles for a route.

    History (median of daily lows) wins once there are enough flight dates; it stays
    "estimated" until it spans enough scan days. Lows far below the seed are dropped
    so a running promotion does not drag the normal down.
    """
    lows = list(daily_lows)
    if seed:
        midpoint = (seed[0] + seed[1]) / 2
        lows = [v for v in lows if v >= 0.5 * midpoint]
    if len(lows) >= MIN_FLIGHT_DATES:
        return Baseline(median(lows), "miles", estimated=scan_days < MIN_SCAN_DAYS)
    if seed:
        return Baseline(midpoint, "miles", estimated=True)
    return None
