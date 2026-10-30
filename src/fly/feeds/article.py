from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from fly.feeds.filter import normalize
from fly.models import Article, PriceLine

# Where each site keeps the post body; everything outside (sidebars, widgets) is ignored.
MAIN_CONTENT = {
    "pontospravoar": "div.entry-content",
    "passageirodeprimeira": "div.box-content[data-content]",
}
AIRLINE_PROGRAM = {"gol": "smiles", "azul": "azul", "latam": "latam"}

BH = re.compile(r"Belo Horizonte|Confins|\bCNF\b")
EXPIRED = re.compile(r"encerrad|esgotad|expirou|expirad")
MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
DATE = re.compile(rf"\b(\d{{1,2}}) de ({'|'.join(MONTHS)})\b")


def _dates(text: str, published: date) -> tuple[date, ...]:
    """'4 de dezembro' -> next occurrence on or after the post's publication date."""
    found = []
    for day, month in DATE.findall(normalize(text)):
        try:
            d = date(published.year, MONTHS[month], int(day))
        except ValueError:
            continue
        if d < published:
            d = d.replace(year=d.year + 1)
        found.append(d)
    return tuple(dict.fromkeys(found))


def _column(header: list[str], *words: str, exclude: str | None = None) -> int | None:
    for i, name in enumerate(header):
        if all(w in name for w in words) and (exclude is None or exclude not in name):
            return i
    return None


def _bh_rows(table, published: date) -> list[PriceLine]:
    rows = table.find_all("tr")
    if not rows:
        return []
    header = [normalize(c.get_text(" ", strip=True)) for c in rows[0].find_all(["th", "td"])]
    origin, dest, airline = _column(header, "origem"), _column(header, "destino"), _column(header, "companhia")
    regular = _column(header, "demais")
    club = _column(header, "clube", exclude="demais")
    dates_col = _column(header, "data")
    if origin is None or (regular is None and club is None):
        return []
    lines = []
    for row in rows[1:]:
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < len(header) or not BH.search(cells[origin]):
            continue
        company = cells[airline] if airline is not None else ""
        program = AIRLINE_PROGRAM.get(normalize(company).strip())
        # The traveler has Clube Azul but not Clube Smiles: club prices only count for Azul.
        col = club if (program == "azul" and club is not None) else (regular if regular is not None else club)
        digits = re.sub(r"\D", "", cells[col])
        lines.append(PriceLine(
            origin=cells[origin],
            destination=cells[dest] if dest is not None else "",
            airline=company,
            program=program,
            miles=int(digits) if digits else None,
            cash_brl=None,
            dates=_dates(cells[dates_col], published) if dates_col is not None else (),
            per_segment="trecho" in header[col],
        ))
    return lines


def extract_article(html: str, feed: str, url: str, published: date) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one(MAIN_CONTENT[feed])
    if main is None:
        return Article(url, "", False, (), (), False)
    text = " ".join(main.get_text(" ", strip=True).split())
    prices = [line for table in main.find_all("table") for line in _bh_rows(table, published)]
    return Article(
        url=url,
        text=text,
        bh_mentioned=bool(BH.search(text)),
        bh_prices=tuple(prices),
        dates=_dates(text, published),
        expired=bool(EXPIRED.search(normalize(text))),
    )
