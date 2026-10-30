from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fly.models import PostDecision, SourceState

PROGRAM_NAMES = {"smiles": "Smiles", "azul": "Azul", "latam": "LATAM Pass"}
FEED_NAMES = {"passageirodeprimeira": "Passageiro de Primeira", "pontospravoar": "Pontos pra Voar"}
DIGEST_MAX_ITEMS = 15
MAX_DATES = 3


def _int(n: float) -> str:
    return f"{round(n):,}".replace(",", ".")


def _brl(v: Decimal) -> str:
    cents = v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole, frac = f"{cents:,.2f}".split(".")
    return f"R$ {whole.replace(',', '.')},{frac}"


def _iata(place: str, fallback: str) -> str:
    m = re.search(r"\(([A-Z]{3})\)", place)
    return m.group(1) if m else fallback


def _program(d: PostDecision) -> str:
    line = d.price
    return PROGRAM_NAMES.get(line.program, line.airline) if line else ""


def _route(d: PostDecision) -> str:
    origin = _iata(d.price.origin, "BH") if d.price else "BH"
    dest = d.destination.iata if d.destination else "?"
    return f"{origin} → {dest}"


def format_post_alert(d: PostDecision, lowest_seen: int | None, brl: Decimal | None) -> str:
    line = d.price
    trip = "por trecho" if line.per_segment else "ida e volta"
    estimated = " — referência estimada" if d.baseline.estimated else ""
    lines = [
        f"🔥 PROMOÇÃO: {round(d.discount * 100)}% abaixo do normal",
        f"{_route(d)} ({d.destination.city})",
        f"{_program(d)} · {_int(line.miles)} milhas {trip} (normal ~{_int(d.baseline.value)}{estimated})",
    ]
    if brl is not None:
        lines.append(f"≈ {_brl(brl)}")
    if line.dates:
        lines.append("Datas: " + ", ".join(f"{x:%d/%m/%Y}" for x in line.dates[:MAX_DATES]))
    if lowest_seen is not None:
        lines.append(f"Menor já visto: {_int(lowest_seen)} milhas")
    lines.append(f"{FEED_NAMES.get(d.item.feed, d.item.feed)}: {d.item.title}")
    lines.append(d.item.url)
    return "\n".join(lines)


def format_digest_line(d: PostDecision) -> str:
    if d.discount is not None and d.price is not None and d.price.miles:
        return (f"• {_route(d)} · {_int(d.price.miles)} milhas {_program(d)}"
                f" (-{round(d.discount * 100)}%) — {d.item.url}")
    return f"• {d.item.title} — {d.reason} — {d.item.url}"


def _source_status(s: SourceState) -> str:
    return f"{s.name} com problema" if s.status == "paused" or s.failure_streak > 0 else f"{s.name} ok"


def format_feed_digest(lines: list[str], states: list[SourceState], day: date) -> str:
    header = f"📋 Resumo fly — {day:%d/%m}"
    body = "\n".join(lines[:DIGEST_MAX_ITEMS]) if lines else "Nenhuma promoção nova de interesse nas últimas 24h."
    sources = "Fontes: " + ", ".join(_source_status(s) for s in states)
    return f"{header}\n\n{body}\n\n{sources}"


def format_health(state: SourceState) -> str:
    return (
        f"⚠️ fly: fonte {state.name} com problema ({state.last_error})"
        f" — {state.failure_streak} falhas seguidas."
    )
