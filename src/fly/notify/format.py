from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fly.catalog import Destination
from fly.models import Deal, FareQuote, SourceState

PROGRAM_NAMES = {"smiles": "Smiles", "azul": "Azul"}
DIGEST_MAX_ITEMS = 10


def _int(n: float) -> str:
    return f"{round(n):,}".replace(",", ".")


def _brl(v: Decimal) -> str:
    cents = v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole, frac = f"{cents:,.2f}".split(".")
    return f"R$ {whole.replace(',', '.')},{frac}"


def _program(source: str) -> str:
    return PROGRAM_NAMES.get(source, source)


def _price(q: FareQuote) -> str:
    if q.miles is not None:
        return f"{_int(q.miles)} milhas"
    return _brl(q.cash_brl) if q.cash_brl is not None else "preço indisponível"


def format_alert(
    deal: Deal,
    dest: Destination,
    ret: FareQuote | None,
    brl: Decimal | None,
    link: str,
    has_balance: bool,
) -> str:
    q = deal.quote
    estimated = " — referência estimada" if deal.baseline.estimated else ""
    lines = [
        f"🔥 PROMOÇÃO: {round(deal.discount * 100)}% abaixo do normal",
        f"{q.route.origin} → {q.route.destination} ({dest.city})",
        f"{q.flight_date:%d/%m/%Y} · {_program(q.source)}",
        f"{_price(q)} (normal ~{_int(deal.baseline.value)}{estimated})",
    ]
    if brl is not None:
        lines.append(f"≈ {_brl(brl)}")
    if has_balance:
        lines.append("✅ Dá para emitir com seu saldo")
    if ret is None:
        lines.append("Volta: nenhuma encontrada ainda")
    else:
        lines.append(f"Volta: {ret.flight_date:%d/%m/%Y} por {_price(ret)} ({_program(ret.source)})")
    lines.append(link)
    return "\n".join(lines)


def _source_status(s: SourceState) -> str:
    if s.status == "paused" and s.paused_until is not None:
        return f"{s.name} pausada até {s.paused_until:%H:%M}"
    return f"{s.name} ok"


def format_digest(
    deals: list[tuple[Deal, Destination]],
    states: list[SourceState],
    routes_checked: int,
    day: date,
) -> str:
    header = f"📋 Resumo fly — {day:%d/%m}"
    if deals:
        top = sorted(deals, key=lambda pair: pair[0].discount, reverse=True)[:DIGEST_MAX_ITEMS]
        body = "\n".join(
            f"• {d.quote.route.origin} → {d.quote.route.destination} {d.quote.flight_date:%d/%m}"
            f" · {_price(d.quote)} (-{round(d.discount * 100)}%)"
            for d, _ in top
        )
    else:
        body = f"Nada entre 30% e 50% abaixo do normal hoje. Rotas verificadas: {routes_checked}."
    sources = "Fontes: " + ", ".join(_source_status(s) for s in states)
    return f"{header}\n\n{body}\n\n{sources}"


def format_health(state: SourceState) -> str:
    return (
        f"⚠️ fly: fonte {state.name} com problema ({state.last_error})"
        f" — {state.failure_streak} falhas seguidas."
    )
