"""Regression tests for the final branch review findings (I1-I7)."""
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from conftest import item
from fly.baseline import load_seeds
from fly.catalog import load_catalog
from fly.config import load_settings
from fly.feeds.article import extract_article, parse_miles
from fly.feeds.decide import decide
from fly.feeds.filter import is_generic, match_destination
from fly.feeds.reader import FetchError, RobotsGate, fetch_text, parse_feed
from fly.models import Article, PriceLine

CAT = load_catalog()
SEEDS = load_seeds()
S = load_settings(Path("config/fly.toml"), Path("/nonexistent.env"))
NOW = datetime(2026, 10, 29, 10, 0)
FRESH = NOW - timedelta(hours=2)
PUB = date(2026, 10, 29)


def line(miles, dest="Lisboa (LIS)", dates=(date(2027, 2, 10),), per_segment=True):
    return PriceLine("Belo Horizonte (CNF)", dest, "TAP", "smiles", miles, None, dates, per_segment)


def art(*lines, dates=()):
    return Article("u", "texto", True, tuple(lines), dates, False)


# I1 — robustness
def test_feed_item_without_pubdate_is_skipped():
    xml = """<rss><channel>
    <item><title>Sem data</title><link>https://x/a</link></item>
    <item><title>Com data</title><link>https://x/b</link><pubDate>Thu, 29 Oct 2026 12:00:00 +0000</pubDate></item>
    </channel></rss>"""
    assert [i.url for i in parse_feed(xml, "pontospravoar")] == ["https://x/b"]


def test_too_many_redirects_is_fetch_error():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        raise httpx.TooManyRedirects("loop", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(FetchError):
        fetch_text(client, RobotsGate(client), "https://x.test/post")


# I2 — silent format changes
def test_feed_without_items_is_an_error():
    with pytest.raises(FetchError):
        parse_feed("<rss><channel><title>vazio</title></channel></rss>", "pontospravoar")


# I3 — date window per BH line
def test_bh_line_before_window_is_ignored():
    d = decide(item("Voe para Lisboa a partir de 25 mil milhas", published_at=FRESH),
               art(line(25000, dates=(date(2026, 12, 4),)), line(30000)), CAT, SEEDS, S, NOW)
    assert d.tier == "alert" and d.price.miles == 30000


def test_article_dates_never_drop_a_bh_line_without_dates():
    d = decide(item("Voe para Lisboa a partir de 40 mil milhas", published_at=FRESH),
               art(line(40000, dates=()), dates=(date(2026, 11, 5),)), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("digest", "confira as datas")


# I4 — destination matching
def test_destination_after_para_beats_origin():
    assert match_destination("Voos de Fortaleza e Belo Horizonte para Lisboa a partir de 40 mil", CAT).iata == "LIS"


def test_christmas_is_not_natal_airport():
    assert match_destination("Promoção de Natal: voe para Lisboa", CAT).iata == "LIS"


@pytest.mark.parametrize("text,iata", [
    ("Voos para o Chile a partir de 20 mil milhas", "SCL"),
    ("LATAM Pass oferece voos para destinos colombianos", "BOG"),
    ("Passagens para a Argentina", "EZE"),
    ("Voe para a Espanha", "MAD"),
])
def test_country_aliases(text, iata):
    assert match_destination(text, CAT).iata == iata


def test_region_words_are_generic():
    assert is_generic("Voe para a Europa a partir de 40 mil milhas")
    assert is_generic("Passagens para o Nordeste com milhas")


def test_bh_row_for_other_catalog_destination_is_used():
    d = decide(item("Voos de Fortaleza e BH a partir de 40 mil milhas", published_at=FRESH),
               art(line(40000)), CAT, SEEDS, S, NOW)
    assert d.destination.iata == "LIS" and d.tier == "alert"


# I5 — unknown fare basis
def test_price_column_without_trecho_is_ambiguous():
    html = """<div class="entry-content"><table>
    <tr><th>Origem</th><th>Destino</th><th>Companhia Aérea</th><th>Demais Clientes</th><th>Datas</th></tr>
    <tr><td>Belo Horizonte (CNF)</td><td>Maceió (MCZ)</td><td>GOL</td><td>30.000</td><td>15 de janeiro</td></tr>
    </table></div>"""
    [bh_line] = extract_article(html, "pontospravoar", "u", PUB).bh_prices
    assert bh_line.per_segment is None
    d = decide(item("Voe para Maceió a partir de 30 mil milhas", published_at=FRESH), art(replace(bh_line)), CAT, SEEDS, S, NOW)
    assert (d.tier, d.reason) == ("digest", "sai de BH — confira se o preço é por trecho")


def test_round_trip_price_marks_baseline_estimated():
    d = decide(item("Voe para Maceió a partir de 30 mil milhas", published_at=FRESH),
               art(line(30000, dest="Maceió (MCZ)", per_segment=False)), CAT, SEEDS, S, NOW)
    assert d.tier == "alert" and d.baseline.estimated  # 15000 vs 35000 dev seed, halved -> estimated


# I6 — miles parsing
@pytest.mark.parametrize("cell,miles", [
    ("46.500", 46500),
    ("46 mil", 46000),
    ("27,5 mil", 27500),
    ("27.500 + R$ 50,00", 27500),
    ("27.500 / 29.000", 27500),
    ("12", None),
    ("—", None),
])
def test_parse_miles(cell, miles):
    assert parse_miles(cell) == miles


# I7 — best discount, not cheapest miles
def test_generic_post_picks_best_discount():
    d = decide(item("Confira passagens pelo Brasil e Europa a partir de 15 mil milhas", published_at=FRESH),
               art(line(15000, dest="Brasília (BSB)"), line(40000)), CAT, SEEDS, S, NOW)
    assert d.destination.iata == "LIS" and d.tier == "alert"
