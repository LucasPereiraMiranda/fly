import pytest

from fly.catalog import Destination, load_catalog, routes
from fly.models import Route


def test_catalog_has_priorities_and_no_excluded():
    cat = load_catalog()
    iatas = {d.iata for d in cat}
    assert {"MCZ", "REC", "SSA", "FLN", "POA"} <= iatas
    assert all(d.priority == "alta" for d in cat if d.iata in {"MCZ", "FLN"})
    assert "SCL" in iatas and next(d for d in cat if d.iata == "SCL").priority == "media"
    assert {"BKK", "NRT"} & iatas
    assert not iatas & {"GIG", "SDU", "GRU", "CGH", "VCP"}
    assert all(d.country != "US" for d in cat)


def test_excluded_destination_rejected(tmp_path):
    p = tmp_path / "d.toml"
    p.write_text(
        '[[destination]]\niata="GRU"\ncity="Sao Paulo"\nregion="sudeste"\n'
        'priority="alta"\ncountry="BR"\n'
    )
    with pytest.raises(ValueError):
        load_catalog(p)


def test_us_destination_rejected(tmp_path):
    p = tmp_path / "d.toml"
    p.write_text(
        '[[destination]]\niata="MIA"\ncity="Miami"\nregion="america_norte"\n'
        'priority="baixa"\ncountry="US"\n'
    )
    with pytest.raises(ValueError):
        load_catalog(p)


def test_routes_both_directions():
    cat = [Destination("MCZ", "Maceio", "nordeste", "alta", "BR")]
    assert [r for r, _ in routes(cat, "CNF")] == [Route("CNF", "MCZ"), Route("MCZ", "CNF")]
