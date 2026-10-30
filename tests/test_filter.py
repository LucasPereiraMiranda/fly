from conftest import item
from fly.catalog import load_catalog
from fly.feeds.filter import is_fare_post, is_generic, match_destination

CAT = load_catalog()


def test_fare_post_vs_card_promo():
    assert is_fare_post(item("Alerta PPV! Viaje para Montevidéu a partir de 27.500 milhas Smiles"))
    assert is_fare_post(item("Voe para Joanesburgo a partir de R$ 1.296 ou 82 mil milhas Smiles + taxas"))
    assert is_fare_post(item("Alerta PPV! Confira passagens pelo Brasil a partir de 3 mil milhas LATAM Pass"))
    assert not is_fare_post(item("Livelo oferece até 96 mil pontos na assinatura dos Clubes"))
    assert not is_fare_post(item("Peça o Cartão Azul Itaú Platinum e ganhe 16 mil pontos"))
    assert not is_fare_post(item("Últimas horas para enviar milhas Smiles para o ALL Accor com até 25% de bônus"))
    assert not is_fare_post(item("Hotéis perto da praia: confira diárias a partir de R$ 191"))


def test_match_destination_accents_and_iata():
    assert match_destination("Viaje para Montevideu a partir de", CAT).iata == "MVD"
    assert match_destination("entre São Paulo (GRU) e Maceió (MCZ)", CAT).iata == "MCZ"
    assert match_destination("Voos para o Japão com milhas", CAT).iata in {"NRT", "HND"}
    assert match_destination("Voe para Joanesburgo", CAT) is None


def test_match_destination_leftmost_wins():
    assert match_destination("Lisboa e Madri a partir de 50 mil milhas", CAT).iata == "LIS"


def test_excluded_city_not_matched():
    assert match_destination("Promoção para o Rio de Janeiro", CAT) is None


def test_generic():
    assert is_generic("Confira passagens pelo Brasil a partir de 3 mil milhas")
    assert is_generic("Voos nacionais a partir de 5 mil milhas")
    assert not is_generic("Viaje para Montevidéu")
