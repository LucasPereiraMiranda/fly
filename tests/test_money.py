from decimal import Decimal

from conftest import quote
from fly.money import brl_equivalent


def test_brl_equivalent_miles():
    q = quote(source="smiles", miles=44800, taxes_brl=Decimal("50.00"))
    assert brl_equivalent(q, {"smiles": Decimal("16.84")}) == Decimal("804.432")


def test_brl_equivalent_cash():
    q = quote(source="latam_cash", miles=None, cash_brl=Decimal("399.90"))
    assert brl_equivalent(q, {"smiles": Decimal("16.84")}) == Decimal("399.90")


def test_brl_equivalent_unknown_program_is_none():
    assert brl_equivalent(quote(source="other"), {"smiles": Decimal("16.84")}) is None
