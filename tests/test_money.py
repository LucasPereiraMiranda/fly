from decimal import Decimal

from fly.money import brl_equivalent


def test_brl_equivalent_miles():
    assert brl_equivalent(44800, "smiles", {"smiles": Decimal("16.84")}) == Decimal("754.432")


def test_brl_equivalent_unknown_program_is_none():
    assert brl_equivalent(44800, "tap", {"smiles": Decimal("16.84")}) is None
