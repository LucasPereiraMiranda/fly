from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

import httpx

from fly.baseline import Seeds
from fly.catalog import Destination
from fly.config import Settings
from fly.db import Database
from fly.feeds.article import extract_article
from fly.feeds.decide import decide
from fly.feeds.filter import match_destination
from fly.feeds.reader import FetchError, FetchNetworkError, RobotsGate, fetch_text, parse_feed
from fly.health import needs_health_notice, on_error, on_network_error, on_success
from fly.models import Article, FeedItem, PostDecision
from fly.money import brl_equivalent
from fly.notify.format import format_digest_line, format_feed_digest, format_health, format_post_alert

log = logging.getLogger(__name__)
DIGEST_WINDOW = timedelta(hours=24)
RUN_SOURCE = "fly"
ARTICLE_SUFFIX = "-artigo"


def _sources(settings: Settings) -> list[str]:
    """Health sources: each feed, plus each feed's article layout."""
    return [*settings.feeds, *(f"{name}{ARTICLE_SUFFIX}" for name in settings.feeds)]


@dataclass
class FeedReport:
    new_posts: int = 0
    alerts_sent: int = 0
    failed_feeds: list[str] = field(default_factory=list)


def _segment_miles(miles: int, per_segment: bool) -> int:
    return miles if per_segment else miles // 2


def _record_prices(db: Database, article: Article, catalog: list[Destination], now: datetime) -> None:
    for line in article.bh_prices:
        dest = match_destination(line.destination, catalog)
        if line.miles and line.program and dest:
            db.add_price_seen(line.program, dest.iata, _segment_miles(line.miles, line.per_segment), now)


def _alert_text(db: Database, d: PostDecision, settings: Settings) -> str:
    line = d.price
    miles = _segment_miles(line.miles, line.per_segment)
    lowest = db.lowest_seen(line.program, d.destination.iata) if line.program else None
    brl = brl_equivalent(miles, line.program, settings.milheiro_brl) if line.program else None
    return format_post_alert(d, lowest, brl)


def _read_feed(client: httpx.Client, gate: RobotsGate, db: Database, name: str, url: str):
    state = db.get_state(name)
    try:
        items = parse_feed(fetch_text(client, gate, url), name)
    except FetchNetworkError as exc:
        db.save_state(on_network_error(state, str(exc)))
        return None
    except FetchError as exc:
        db.save_state(on_error(state, str(exc)))
        return None
    except Exception as exc:  # unexpected parse failure: count it, never crash the round
        log.exception("feed %s failed", name)
        db.save_state(on_error(state, type(exc).__name__))
        return None
    db.save_state(on_success(state))
    return items


def _track_layout(db: Database, feed: str, article: Article) -> None:
    """An article without the expected main content means the site changed its layout."""
    name = f"{feed}{ARTICLE_SUFFIX}"
    state = db.get_state(name)
    db.save_state(on_error(state, "layout do artigo mudou") if not article.text else on_success(state))


def _process(item: FeedItem, *, db: Database, client: httpx.Client, gate: RobotsGate, notifier,
             catalog: list[Destination], seeds: Seeds, settings: Settings, now: datetime) -> bool:
    """Decide one new post and record it; returns True when an alert was delivered."""
    first = decide(item, None, catalog, seeds, settings, now)
    if first.tier == "drop":  # no need to open the article
        db.record_post(first, None, None, now)
        return False
    try:
        html = fetch_text(client, gate, item.url)
        article = extract_article(html, item.feed, item.url, item.published_at.date())
    except FetchError as exc:
        log.info("article unavailable %s: %s", item.url, exc)
        article = None
    if article is not None:
        _track_layout(db, item.feed, article)
        _record_prices(db, article, catalog, now)
    d = decide(item, article, catalog, seeds, settings, now)
    if d.tier == "alert":
        message = _alert_text(db, d, settings)
        db.record_post(d, message, None, now)
        if notifier.send(message):
            db.mark_sent(item.url)
            return True
    elif d.tier == "digest":
        db.record_post(d, None, format_digest_line(d), now)
    else:
        db.record_post(d, None, None, now)
    return False


def run_feeds(*, db: Database, client: httpx.Client, notifier, catalog: list[Destination],
              seeds: Seeds, settings: Settings, now: datetime) -> FeedReport:
    report = FeedReport()

    # Alerts that could not be delivered before (e.g. Telegram unreachable) go out first.
    for url, message in db.pending_alerts(now, settings.post_max_age_hours):
        if notifier.send(message):
            db.mark_sent(url)
            report.alerts_sent += 1

    gate = RobotsGate(client)
    for name, feed_url in settings.feeds.items():
        items = _read_feed(client, gate, db, name, feed_url)
        if items is None:
            report.failed_feeds.append(name)
            continue
        for item in items:
            if db.post_seen(item.url):
                continue
            report.new_posts += 1
            try:
                if _process(item, db=db, client=client, gate=gate, notifier=notifier,
                            catalog=catalog, seeds=seeds, settings=settings, now=now):
                    report.alerts_sent += 1
            except Exception:  # one odd post must never silence the whole round
                log.exception("post failed %s", item.url)
                failed = PostDecision(item, "digest", "erro ao processar — confira", None, None, None, None)
                db.record_post(failed, None, format_digest_line(failed), now)

    for name in _sources(settings):
        state = db.get_state(name)
        if needs_health_notice(state) and notifier.send(format_health(state)):
            db.save_state(replace(state, notified=True))
    return report


def build_feed_digest(*, db: Database, settings: Settings, now: datetime) -> str:
    lines = db.digest_lines(now - DIGEST_WINDOW)
    return format_feed_digest(lines, [db.get_state(n) for n in _sources(settings)], now.date())


def run_guarded(job: Callable[[], None], *, db: Database, notifier) -> None:
    """Run a scheduled job; on any crash, log it and tell the traveler once until it recovers."""
    state = db.get_state(RUN_SOURCE)
    try:
        job()
    except Exception as exc:
        log.exception("fly job failed")
        state = on_error(state, type(exc).__name__)
        if not state.notified and notifier.send(
            f"⚠️ fly: execução falhou ({type(exc).__name__}). Veja data/logs/fly.log."
        ):
            state = replace(state, notified=True)
        db.save_state(state)
        return
    db.save_state(on_success(state))
