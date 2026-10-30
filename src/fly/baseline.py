from __future__ import annotations

import tomllib
from pathlib import Path
from typing import NamedTuple

from fly.catalog import Destination
from fly.models import Baseline


class Seeds(NamedTuple):
    routes: dict[tuple[str, str], tuple[int, int]]  # (program, destination IATA) -> range
    regions: dict[str, tuple[int, int]]  # catalog region -> range


def load_seeds(path: Path = Path("config/seeds.toml")) -> Seeds:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return Seeds(
        routes={(s["program"], s["destination"]): (s["min"], s["max"]) for s in raw.get("seed", [])},
        regions={s["region"]: (s["min"], s["max"]) for s in raw.get("region_seed", [])},
    )


def normal_for_offer(seeds: Seeds, program: str | None, dest: Destination) -> Baseline | None:
    """Normal price in miles: the route's own seed if any, else the region's (estimated)."""
    route = seeds.routes.get((program, dest.iata)) if program else None
    if route:
        return Baseline(sum(route) / 2, "miles", estimated=False)
    region = seeds.regions.get(dest.region)
    if region:
        return Baseline(sum(region) / 2, "miles", estimated=True)
    return None
