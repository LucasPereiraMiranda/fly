from __future__ import annotations

import re
import unicodedata

from fly.catalog import Destination
from fly.models import FeedItem

FARE_WORDS = re.compile(r"\b(passage\w*|voo\w*|voe|voar|viaje\w*|trechos?|emiss\w*)\b")
PRICE_WORDS = re.compile(r"(milhas|pontos|r\$)")
NOT_FARE_TITLE = re.compile(
    r"\b(cartao|clube\w*|assinatura\w*|transfer\w*|bonus|hote\w*|hosped\w*|diarias?|cashback|"
    r"ingressos?|cupo\w*|acumul\w*)\b"
)
GENERIC = re.compile(r"\b(pelo brasil|voos nacionais|destinos nacionais|nacionais|nacional)\b")


def normalize(text: str) -> str:
    """Lowercase without accents, so 'Maceió' and 'maceio' compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def is_fare_post(item: FeedItem) -> bool:
    title = normalize(item.title)
    text = f"{title} {normalize(item.summary)}"
    if NOT_FARE_TITLE.search(title):
        return False
    return bool(FARE_WORDS.search(text) and PRICE_WORDS.search(text))


def _names(dest: Destination) -> list[str]:
    base_city = dest.city.split(" (")[0]
    return [normalize(n) for n in (base_city, *dest.aliases)]


def match_destination(text: str, catalog: list[Destination]) -> Destination | None:
    """The catalog destination mentioned earliest in the text, by city, alias or (IATA)."""
    norm = normalize(text)
    best: tuple[int, int, Destination] | None = None
    for order, dest in enumerate(catalog):
        patterns = [rf"\b{re.escape(n)}\b" for n in _names(dest)] + [rf"\({dest.iata.lower()}\)"]
        for pattern in patterns:
            m = re.search(pattern, norm)
            if m and (best is None or (m.start(), order) < best[:2]):
                best = (m.start(), order, dest)
    return best[2] if best else None


def is_generic(text: str) -> bool:
    return bool(GENERIC.search(normalize(text)))
