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
GENERIC = re.compile(
    r"\b(pelo brasil|voos nacionais|destinos nacionais|nacionais|nacional|europa|nordeste|"
    r"america do sul|asia|sudeste asiatico|caribe|oriente medio)\b"
)
TO_PREFIX = re.compile(r"(\b(para|a|ate)\s+((o|a|os|as)\s+)?|→\s*)$")


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


def _is_holiday(norm: str, start: int, end: int) -> bool:
    """'Promoção de Natal:' is Christmas, not the airport NAT."""
    return norm[start:end] == "natal" and (norm[:start].endswith("de ") or norm[end:].lstrip().startswith(":"))


def match_destination(text: str, catalog: list[Destination]) -> Destination | None:
    """The catalog destination the text points to, by city, alias or (IATA).

    A place right after "para"/"a"/"até" wins (in "Fortaleza a Lisboa" the destination is
    Lisboa); otherwise the earliest mention.
    """
    norm = normalize(text)
    found: list[tuple[bool, int, int, Destination]] = []
    for order, dest in enumerate(catalog):
        patterns = [rf"\b{re.escape(n)}\b" for n in _names(dest)] + [rf"\({dest.iata.lower()}\)"]
        for pattern in patterns:
            for m in re.finditer(pattern, norm):
                if _is_holiday(norm, m.start(), m.end()):
                    continue
                after_to = bool(TO_PREFIX.search(norm[:m.start()]))
                found.append((not after_to, m.start(), order, dest))
    return min(found, key=lambda f: f[:3])[3] if found else None


def is_generic(text: str) -> bool:
    return bool(GENERIC.search(normalize(text)))
