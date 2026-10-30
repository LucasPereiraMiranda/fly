from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

from conftest import item
from fly.baseline import load_seeds
from fly.catalog import load_catalog
from fly.config import load_settings
from fly.feeds.decide import decide
from fly.models import Article, PriceLine

CAT = load_catalog()
SEEDS = load_seeds()
S = load_settings(Path("config/fly.toml"), Path("/nonexistent.env"))
NOW = datetime(2026, 10, 29, 10, 0)
FRESH = NOW - timedelta(hours=2)
MVD_TITLE = "Alerta PPV! Viaje para Montevidéu a partir de 28 mil milhas Smiles"


def bh(miles, dest="Montevidéu (MVD)", dates=(date(2027, 1, 15),)):
    return PriceLine("Belo Horizonte (CNF)", dest, "GOL", "smiles", miles, None, dates, True)


def art(bh_mentioned=True, bh_prices=(), dates=(), expired=False):
    return Article("u", "texto", bh_mentioned, bh_prices, dates, expired)


def fresh(title):
    return item(title, published_at=FRESH)


def test_alert_when_bh_price_half_of_normal():  # america_sul normal 60000; 28000 -> 53%
    d = decide(fresh(MVD_TITLE), art(bh_prices=(bh(28000),)), CAT, SEEDS, S, NOW)
    assert d.tier == "alert" and d.destination.iata == "MVD" and round(d.discount, 2) == 0.53
    assert d.price.miles == 28000 and d.baseline.estimated


def test_old_post_goes_to_digest():
    d = decide(item(MVD_TITLE, published_at=NOW - timedelta(hours=30)), art(bh_prices=(bh(28000),)), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("digest", "promoção de mais de 24h")


def test_digest_band_and_small_discount():
    assert decide(fresh(MVD_TITLE), art(bh_prices=(bh(40000),)), CAT, SEEDS, S, NOW).tier == "digest"  # 33%
    d = decide(fresh(MVD_TITLE), art(bh_prices=(bh(48000),)), CAT, SEEDS, S, NOW)  # 20%
    assert (d.tier, d.reason) == ("drop", "desconto pequeno")


def test_cheapest_bh_line_wins():
    d = decide(fresh(MVD_TITLE), art(bh_prices=(bh(48000), bh(28000))), CAT, SEEDS, S, NOW)
    assert d.price.miles == 28000


def test_no_bh_goes_to_digest():
    d = decide(fresh(MVD_TITLE), art(bh_mentioned=False), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("digest", "confira se sai de BH")


def test_bh_without_price_goes_to_digest():
    d = decide(fresh(MVD_TITLE), art(), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("digest", "sai de BH — confira o preço")


def test_non_fare_and_unknown_destination_dropped():
    assert decide(fresh("Peça o cartão e ganhe 16 mil pontos"), None, CAT, SEEDS, S, NOW).reason == "nao e passagem"
    d = decide(fresh("Voe para Joanesburgo a partir de 82 mil milhas"), None, CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("drop", "destino fora do catalogo")


def test_article_unavailable_goes_to_digest():
    d = decide(fresh(MVD_TITLE), None, CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("digest", "artigo indisponivel — confira")


def test_dates_before_window_dropped():
    soon = (date(2026, 11, 20),)
    d = decide(fresh(MVD_TITLE), art(dates=soon, bh_prices=(bh(28000, dates=soon),)), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("drop", "datas antes da janela")


def test_some_date_in_window_keeps_post():
    dates = (date(2026, 11, 20), date(2027, 2, 1))
    assert decide(fresh(MVD_TITLE), art(dates=dates, bh_prices=(bh(28000),)), CAT, SEEDS, S, NOW).tier == "alert"


def test_expired_dropped():
    d = decide(fresh(MVD_TITLE), art(expired=True, bh_prices=(bh(28000),)), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("drop", "encerrada")


def test_generic_post_takes_destination_from_bh_row():
    d = decide(fresh("Confira passagens pelo Brasil a partir de 3 mil milhas LATAM Pass"),
               art(bh_prices=(bh(9000, dest="Maceió (MCZ)"),)), CAT, SEEDS, S, NOW)
    assert d.destination.iata == "MCZ" and d.tier == "alert"  # 9000 vs 35000 (dev seed)


def test_generic_without_bh_dropped():
    d = decide(fresh("Confira passagens pelo Brasil a partir de 3 mil milhas"), art(bh_mentioned=False), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("drop", "generico sem BH")


def test_round_trip_price_halved():
    line = replace(bh(56000), per_segment=False)  # 28000 per segment
    assert decide(fresh(MVD_TITLE), art(bh_prices=(line,)), CAT, SEEDS, S, NOW).tier == "alert"


def test_cash_only_bh_price_goes_to_digest():
    line = replace(bh(None), cash_brl=1296)
    d = decide(fresh(MVD_TITLE), art(bh_prices=(line,)), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("digest", "sai de BH por R$ — sem referência em R$")
