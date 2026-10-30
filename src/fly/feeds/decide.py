from __future__ import annotations

from datetime import datetime, timedelta

from fly.baseline import Seeds, normal_for_offer
from fly.catalog import Destination
from fly.config import Settings
from fly.detect import discount_tier
from fly.feeds.filter import is_fare_post, is_generic, match_destination
from fly.models import Article, FeedItem, PostDecision, PriceLine


def _bh_line(article: Article, dest: Destination | None,
             catalog: list[Destination]) -> tuple[PriceLine | None, Destination | None, bool]:
    """Cheapest BH line for the post's destination (or any catalog destination for generic posts).

    Returns the line with miles, its destination, and whether only cash prices were found.
    """
    matched = []
    for line in article.bh_prices:
        line_dest = match_destination(line.destination, catalog)
        if line_dest is not None and (dest is None or line_dest == dest):
            matched.append((line, line_dest))
    with_miles = [(line, d) for line, d in matched if line.miles]
    if not with_miles:
        cash_only = any(line.cash_brl is not None for line, _ in matched)
        return None, dest, cash_only
    line, line_dest = min(with_miles, key=lambda pair: pair[0].miles)
    return line, line_dest, False


def decide(item: FeedItem, article: Article | None, catalog: list[Destination], seeds: Seeds,
           settings: Settings, now: datetime) -> PostDecision:
    def result(tier, reason, dest=None, line=None, baseline=None, discount=None):
        return PostDecision(item, tier, reason, dest, line, baseline, discount)

    if not is_fare_post(item):
        return result("drop", "nao e passagem")
    text = f"{item.title} {item.summary}"
    dest = match_destination(text, catalog)
    if dest is None and not is_generic(text):
        return result("drop", "destino fora do catalogo")
    if article is None:
        return result("digest", "artigo indisponivel — confira", dest)
    if article.expired:
        return result("drop", "encerrada", dest)
    window_start = now.date() + timedelta(days=settings.window_min_days)
    if article.dates and max(article.dates) < window_start:
        return result("drop", "datas antes da janela", dest)
    if not article.bh_mentioned:
        if dest is None:
            return result("drop", "generico sem BH")
        return result("digest", "confira se sai de BH", dest)

    line, dest, cash_only = _bh_line(article, dest, catalog)
    if line is None:
        reason = "sai de BH por R$ — sem referência em R$" if cash_only else "sai de BH — confira o preço"
        return result("digest", reason, dest)
    miles = line.miles if line.per_segment else line.miles / 2
    baseline = normal_for_offer(seeds, line.program, dest)
    if baseline is None:
        return result("digest", "sai de BH — sem preço normal de referência", dest, line)
    discount, tier = discount_tier(miles, baseline, settings.alert_discount, settings.digest_discount)
    if tier is None:
        return result("drop", "desconto pequeno", dest, line, baseline, discount)
    if tier == "alert" and now - item.published_at > timedelta(hours=settings.post_max_age_hours):
        return result("digest", "promoção de mais de 24h", dest, line, baseline, discount)
    return result(tier, "promoção", dest, line, baseline, discount)
