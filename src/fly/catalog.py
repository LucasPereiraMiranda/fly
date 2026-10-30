from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fly.models import Route

Priority = Literal["alta", "media", "baixa"]

# Final destinations the traveler does not want: Rio de Janeiro and Sao Paulo airports.
EXCLUDED_AIRPORTS = frozenset({"GIG", "SDU", "GRU", "CGH", "VCP"})
EXCLUDED_COUNTRIES = frozenset({"US"})
PRIORITIES = ("alta", "media", "baixa")


@dataclass(frozen=True)
class Destination:
    iata: str
    city: str
    region: str
    priority: Priority
    country: str


def load_catalog(path: Path = Path("config/destinations.toml")) -> list[Destination]:
    with path.open("rb") as f:
        raw = tomllib.load(f)
    catalog = [Destination(**entry) for entry in raw["destination"]]
    for d in catalog:
        if d.iata in EXCLUDED_AIRPORTS or d.country in EXCLUDED_COUNTRIES:
            raise ValueError(f"excluded destination in catalog: {d.iata} ({d.country})")
        if d.priority not in PRIORITIES:
            raise ValueError(f"unknown priority for {d.iata}: {d.priority}")
    return catalog


def routes(catalog: list[Destination], origin: str) -> list[tuple[Route, Destination]]:
    pairs: list[tuple[Route, Destination]] = []
    for d in catalog:
        outbound = Route(origin, d.iata)
        pairs.append((outbound, d))
        pairs.append((outbound.reversed(), d))
    return pairs
