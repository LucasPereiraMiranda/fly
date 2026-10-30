from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from conftest import item
from fly.catalog import Destination
from fly.models import Baseline, PostDecision, PriceLine, SourceState
from fly.notify.format import format_digest_line, format_feed_digest, format_health, format_post_alert

MVD = Destination("MVD", "Montevidéu", "america_sul", "media", "UY")
LINE = PriceLine("Belo Horizonte (CNF)", "Montevidéu (MVD)", "GOL", "smiles", 28000, None, (date(2026, 12, 4),), True)
ITEM = replace(item("Alerta PPV! Viaje para Montevidéu"), url="https://pontospravoar.com/alerta-montevideu/")
ALERT = PostDecision(ITEM, "alert", "promoção", MVD, LINE, Baseline(60000, "miles", True), 1 - 28000 / 60000)
OK = SourceState("pontospravoar", "ok", None, 0, 0, None, False)


def test_post_alert_text_exact():
    assert format_post_alert(ALERT, 28000, Decimal("471.52")) == (
        "🔥 PROMOÇÃO: 53% abaixo do normal\n"
        "CNF → MVD (Montevidéu)\n"
        "Smiles · 28.000 milhas por trecho (normal ~60.000 — referência estimada)\n"
        "≈ R$ 471,52\n"
        "Datas: 04/12/2026\n"
        "Menor já visto: 28.000 milhas\n"
        "Pontos pra Voar: Alerta PPV! Viaje para Montevidéu\n"
        "https://pontospravoar.com/alerta-montevideu/"
    )


def test_alert_optional_lines_omitted():
    d = replace(ALERT, baseline=Baseline(60000, "miles", False), price=replace(LINE, dates=(), per_segment=False))
    text = format_post_alert(d, None, None)
    assert "referência estimada" not in text and "≈ R$" not in text
    assert "Datas:" not in text and "Menor já visto" not in text
    assert "28.000 milhas ida e volta" in text


def test_digest_line_with_and_without_discount():
    d = replace(ALERT, tier="digest", discount=1 - 40000 / 60000, price=replace(LINE, miles=40000))
    assert format_digest_line(d) == "• CNF → MVD · 40.000 milhas Smiles (-33%) — https://pontospravoar.com/alerta-montevideu/"
    no_bh = PostDecision(ITEM, "digest", "confira se sai de BH", MVD, None, None, None)
    assert format_digest_line(no_bh) == (
        "• Alerta PPV! Viaje para Montevidéu — confira se sai de BH — https://pontospravoar.com/alerta-montevideu/"
    )


def test_feed_digest_empty_and_paused():
    paused = SourceState("passageirodeprimeira", "paused", datetime(2026, 10, 29, 14, 0), 60, 3, "HTTP 500", False)
    assert format_feed_digest([], [paused, OK], date(2026, 10, 29)) == (
        "📋 Resumo fly — 29/10\n\n"
        "Nenhuma promoção nova de interesse nas últimas 24h.\n\n"
        "Fontes: passageirodeprimeira com problema, pontospravoar ok"
    )


def test_feed_digest_caps_at_fifteen():
    text = format_feed_digest([f"• linha {i}" for i in range(20)], [OK], date(2026, 10, 29))
    assert sum(1 for line in text.splitlines() if line.startswith("• ")) == 15


def test_health_text():
    s = SourceState("pontospravoar", "ok", None, 0, 3, "HTTP 500", False)
    assert format_health(s) == "⚠️ fly: fonte pontospravoar com problema (HTTP 500) — 3 falhas seguidas."
