from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal


def brl_equivalent(miles: int, program: str, milheiro_brl: Mapping[str, Decimal]) -> Decimal | None:
    """Miles valued at the program's price per 1000 miles, or None for an unknown program."""
    if program not in milheiro_brl:
        return None
    return miles * milheiro_brl[program] / 1000
