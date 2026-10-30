from datetime import date
from pathlib import Path

from fly.feeds.article import extract_article

FIXTURES = Path(__file__).parent / "fixtures"
PUB = date(2026, 10, 29)

AZUL_HTML = """<div class="entry-content"><table>
<tr><th>Origem</th><th>Destino</th><th>Companhia Aérea</th><th>Trecho Clube</th><th>Trecho Demais Clientes</th><th>Datas</th></tr>
<tr><td>Belo Horizonte (CNF)</td><td>Recife (REC)</td><td>Azul</td><td>30.000</td><td>33.000</td><td>15 de fevereiro</td></tr>
</table></div>"""


def read(name):
    return (FIXTURES / name).read_text()


def test_ppv_bh_rows_use_non_club_column():
    a = extract_article(read("article_ppv_bh.html"), "pontospravoar", "u", PUB)
    assert a.bh_mentioned and not a.expired
    assert [(p.miles, p.dates, p.program, p.per_segment) for p in a.bh_prices] == [
        (48000, (date(2026, 12, 4),), "smiles", True),
        (45500, (date(2027, 1, 2),), "smiles", True),
    ]
    assert a.bh_prices[0].destination == "Montevidéu (MVD)"


def test_pp_sidebar_bh_ignored():
    a = extract_article(read("article_pp_gru.html"), "passageirodeprimeira", "u", PUB)
    assert not a.bh_mentioned and a.bh_prices == ()
    assert a.dates == (date(2027, 3, 3),)


def test_date_year_rollover():
    html = '<div class="entry-content"><p>Voos em 4 de dezembro e 10 de janeiro</p></div>'
    assert extract_article(html, "pontospravoar", "u", date(2026, 12, 20)).dates == (
        date(2027, 12, 4),
        date(2027, 1, 10),
    )


def test_azul_uses_club_column():
    line = extract_article(AZUL_HTML, "pontospravoar", "u", PUB).bh_prices[0]
    assert (line.miles, line.program) == (30000, "azul")


def test_expired_detected():
    html = '<div class="entry-content"><p>Promoção encerrada. Belo Horizonte</p></div>'
    assert extract_article(html, "pontospravoar", "u", PUB).expired


def test_missing_main_content():
    a = extract_article("<html><body><aside>Belo Horizonte</aside></body></html>", "pontospravoar", "u", PUB)
    assert a.text == "" and not a.bh_mentioned
