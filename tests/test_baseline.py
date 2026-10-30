from fly.baseline import load_seeds, normal_for_offer
from fly.catalog import Destination
from fly.models import Baseline

SEEDS = load_seeds()
MCZ = Destination("MCZ", "Maceió", "nordeste", "alta", "BR")
MVD = Destination("MVD", "Montevidéu", "america_sul", "media", "UY")
XYZ = Destination("XYZ", "Lugar", "antartida", "baixa", "AQ")


def test_route_seed_from_dev_is_not_estimated():
    assert normal_for_offer(SEEDS, "smiles", MCZ) == Baseline(35000, "miles", False)


def test_region_seed_is_estimated():
    assert normal_for_offer(SEEDS, "latam", MVD) == Baseline(60000, "miles", True)


def test_route_seed_is_per_program():
    assert normal_for_offer(SEEDS, "azul", MCZ) == Baseline(35000, "miles", True)  # nordeste region


def test_no_seed_none():
    assert normal_for_offer(SEEDS, "smiles", XYZ) is None
