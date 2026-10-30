from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from fly.baseline import Seeds, normal_for_offer
from fly.catalog import Destination
from fly.config import Settings
from fly.detect import discount_tier
from fly.feeds.filter import is_fare_post, is_generic, match_destination
from fly.models import Article, Baseline, FeedItem, PostDecision, PriceLine


@dataclass(frozen=True)
class _Offer:
    line: PriceLine
    dest: Destination
    baseline: Baseline | None
    discount: float | None
    tier: str | None


def _in_window(line: PriceLine, window_start: date) -> bool:
    return not line.dates or max(line.dates) >= window_start


def _offers(article: Article, dest: Destination | None, catalog: list[Destination], seeds: Seeds,
            settings: Settings, window_start: date) -> tuple[list[_Offer], bool]:
    """BH lines with miles for the post's destination (or any catalog destination as a fallback),
    each priced against its normal. Also says whether lines were found but all fell before the window.
    """
    matched = [(line, d) for line in article.bh_prices
               if line.miles and (d := match_destination(line.destination, catalog)) is not None]
    for_dest = [(line, d) for line, d in matched if d == dest]
    candidates = for_dest or matched
    in_window = [(line, d) for line, d in candidates if _in_window(line, window_start)]
    offers = []
    for line, d in in_window:
        baseline = normal_for_offer(seeds, line.program, d)
        discount = tier = None
        if baseline is not None and line.per_segment is not None:
            miles = line.miles if line.per_segment else line.miles / 2
            if not line.per_segment:  # halving a round-trip price is an estimate
                baseline = replace(baseline, estimated=True)
            discount, tier = discount_tier(miles, baseline, settings.alert_discount, settings.digest_discount)
        offers.append(_Offer(line, d, baseline, discount, tier))
    return offers, bool(candidates) and not in_window


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
    if not article.bh_mentioned:
        if dest is None:
            return result("drop", "generico sem BH")
        return result("digest", "confira se sai de BH", dest)

    window_start = now.date() + timedelta(days=settings.window_min_days)
    offers, all_before_window = _offers(article, dest, catalog, seeds, settings, window_start)
    if all_before_window:
        return result("drop", "datas antes da janela", dest)
    priced = [o for o in offers if o.discount is not None]
    if not priced:
        if any(o.line.per_segment is None for o in offers):
            o = offers[0]
            return result("digest", "sai de BH — confira se o preço é por trecho", o.dest, o.line)
        if offers:
            o = min(offers, key=lambda o: o.line.miles)
            return result("digest", "sai de BH — sem preço normal de referência", o.dest, o.line)
        if any(line.cash_brl is not None for line in article.bh_prices):
            return result("digest", "sai de BH por R$ — sem referência em R$", dest)
        return result("digest", "sai de BH — confira o preço", dest)

    best = max(priced, key=lambda o: o.discount)
    tier = best.tier
    args = (best.dest, best.line, best.baseline, best.discount)
    if tier is None:
        return result("drop", "desconto pequeno", *args)
    if tier == "alert" and now - item.published_at > timedelta(hours=settings.post_max_age_hours):
        return result("digest", "promoção de mais de 24h", *args)
    # Dates only in the article text (e.g. "válida até 5 de novembro") are never a reason to drop,
    # but an alert needs at least one travel date on or after the window start.
    if tier == "alert" and article.dates and max(article.dates) < window_start:
        return result("digest", "confira as datas", *args)
    return result(tier, "promoção", *args)
