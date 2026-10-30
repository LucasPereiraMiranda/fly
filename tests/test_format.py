from datetime import date, datetime
from decimal import Decimal

from conftest import quote
from fly.catalog import Destination
from fly.models import Baseline, Deal, Route, SourceState
from fly.notify.format import format_alert, format_digest, format_health

MCZ = Destination("MCZ", "Maceió", "nordeste", "alta", "BR")
DEAL = Deal(quote(flight_date=date(2026, 11, 11), miles=8000), Baseline(35000, "miles", True), 1 - 8000 / 35000, "alert")
RET = quote(route=Route("MCZ", "CNF"), flight_date=date(2026, 11, 27), miles=18000)
OK = SourceState("smiles", "ok", None, 0, 0, None, False)


def test_alert_text_exact():
    text = format_alert(DEAL, MCZ, RET, Decimal("134.72"), "https://x", has_balance=True)
    assert text == (
        "🔥 PROMOÇÃO: 77% abaixo do normal\n"
        "CNF → MCZ (Maceió)\n"
        "11/11/2026 · Smiles\n"
        "8.000 milhas (normal ~35.000 — referência estimada)\n"
        "≈ R$ 134,72\n"
        "✅ Dá para emitir com seu saldo\n"
        "Volta: 27/11/2026 por 18.000 milhas (Smiles)\n"
        "https://x"
    )


def test_alert_without_return_balance_and_brl():
    deal = Deal(DEAL.quote, Baseline(35000, "miles", False), DEAL.discount, "alert")
    text = format_alert(deal, MCZ, None, None, "https://x", has_balance=False)
    assert "referência estimada" not in text and "≈ R$" not in text and "✅" not in text
    assert "Volta: nenhuma encontrada ainda" in text
    assert "8.000 milhas (normal ~35.000)" in text


def test_digest_empty():
    text = format_digest([], [OK], routes_checked=12, day=date(2026, 10, 29))
    assert text == (
        "📋 Resumo fly — 29/10\n\n"
        "Nada entre 30% e 50% abaixo do normal hoje. Rotas verificadas: 12.\n\n"
        "Fontes: smiles ok"
    )


def test_digest_orders_by_discount_and_shows_paused():
    d40 = Deal(quote(flight_date=date(2026, 11, 11), miles=21000), Baseline(35000, "miles", False), 0.40, "digest")
    d45 = Deal(quote(flight_date=date(2026, 12, 2), miles=19250), Baseline(35000, "miles", False), 0.45, "digest")
    paused = SourceState("smiles", "paused", datetime(2026, 10, 29, 14, 0), 60, 1, "403", False)
    text = format_digest([(d40, MCZ), (d45, MCZ)], [paused], routes_checked=3, day=date(2026, 10, 29))
    lines = text.splitlines()
    assert lines[2] == "• CNF → MCZ 02/12 · 19.250 milhas (-45%)"
    assert lines[3] == "• CNF → MCZ 11/11 · 21.000 milhas (-40%)"
    assert lines[-1] == "Fontes: smiles pausada até 14:00"


def test_digest_caps_at_ten_items():
    deals = [(Deal(quote(miles=21000), Baseline(35000, "miles", False), 0.40, "digest"), MCZ)] * 15
    text = format_digest(deals, [OK], routes_checked=1, day=date(2026, 10, 29))
    assert sum(1 for line in text.splitlines() if line.startswith("• ")) == 10


def test_health_text():
    s = SourceState("smiles", "paused", None, 60, 3, "403", False)
    assert format_health(s) == "⚠️ fly: fonte smiles com problema (403) — 3 falhas seguidas."
