from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

from fly.baseline import normal_for
from fly.catalog import Destination, routes
from fly.config import Settings
from fly.db import Database
from fly.detect import classify, dedupe_key, should_alert
from fly.health import (
    is_available,
    needs_health_notice,
    on_blocked,
    on_error,
    on_network_error,
    on_success,
)
from fly.models import Baseline, Deal, FareQuote, Route
from fly.money import brl_equivalent
from fly.notify.format import format_alert, format_digest, format_health
from fly.scheduler import plan_round
from fly.sources.base import Source, SourceBlocked, SourceError, SourceNetworkError
from fly.trip import best_return

log = logging.getLogger(__name__)

HISTORY_DAYS = 60
PENDING_LOOKBACK_HOURS = 24
RETURN_LOOKBACK_DAYS = 7
DIGEST_LOOKBACK_HOURS = 36
SOURCES_WITH_BALANCE = frozenset({"smiles", "azul"})


@dataclass
class RoundReport:
    scanned: int = 0
    alerts_sent: int = 0
    skipped_sources: list[str] = field(default_factory=list)


def _in_window(day: date, now: datetime, settings: Settings) -> bool:
    today = now.date()
    return (today + timedelta(days=settings.window_min_days)
            <= day <= today + timedelta(days=settings.window_max_days))


def _baseline(db: Database, seeds: Mapping, source: str, route: Route, now: datetime) -> Baseline | None:
    since = now - timedelta(days=HISTORY_DAYS)
    return normal_for(seeds.get((source, route)), db.daily_lows(source, route, since),
                      db.scan_days(source, route, since))


def _classify(quote: FareQuote, baseline: Baseline | None, settings: Settings) -> Deal | None:
    if baseline is None:
        return None
    return classify(quote, baseline, settings.alert_discount, settings.digest_discount)


def _budget(settings: Settings, source: str) -> int:
    return settings.smiles_budget_per_round if source == "smiles" else 0


def _try_alert(*, db, source: Source, notifier, quote: FareQuote, dest: Destination, seeds,
               settings: Settings, now: datetime, pause: Callable[[], None]) -> bool:
    """Reconfirm a candidate alert with a fresh query, then send it once."""
    route = quote.route
    deal = _classify(quote, _baseline(db, seeds, source.name, route, now), settings)
    key = dedupe_key(quote)
    if deal is None or deal.tier != "alert" or not should_alert(quote.miles, db.last_alert_value(key)):
        return False
    pause()
    try:
        fresh = source.fetch_week(route, quote.flight_date)
    except SourceError as exc:
        log.info("reconfirm failed for %s: %s", key, exc)
        return False
    db.add_quotes(fresh)
    same_day = [q for q in fresh if q.flight_date == quote.flight_date and q.miles]
    if not same_day:
        return False
    confirmed = min(same_day, key=lambda q: q.miles)
    deal = _classify(confirmed, deal.baseline, settings)
    if deal is None or deal.tier != "alert":
        log.info("promo vanished on reconfirm: %s", key)
        return False
    since = now - timedelta(days=RETURN_LOOKBACK_DAYS)
    ret = best_return(confirmed, db.latest_quotes(source.name, route.reversed(), since),
                      settings.milheiro_brl, settings.return_min_days, settings.return_max_days)
    text = format_alert(deal, dest, ret, brl_equivalent(confirmed, settings.milheiro_brl),
                        source.link(route, confirmed.flight_date),
                        has_balance=source.name in SOURCES_WITH_BALANCE)
    if not notifier.send(text):
        return False
    db.record_alert(key, confirmed.miles, now)
    return True


def run_round(*, db: Database, sources: Mapping[str, Source], notifier, catalog: list[Destination],
              seeds: Mapping, settings: Settings, now: datetime,
              sleep: Callable[[float], None] = time.sleep) -> RoundReport:
    report = RoundReport()
    dest_of = {route: dest for route, dest in routes(catalog, settings.origin)}
    first = True

    def pause() -> None:
        nonlocal first
        if not first:
            sleep(random.uniform(*settings.smiles_delay_seconds))
        first = False

    for name, source in sources.items():
        state = db.get_state(name)
        if not is_available(state, now):
            report.skipped_sources.append(name)
            continue
        # Alerts that could not be sent before (e.g. Telegram unreachable) go out first.
        recent = now - timedelta(hours=PENDING_LOOKBACK_HOURS)
        for route, dest in dest_of.items():
            for q in db.latest_quotes(name, route, recent):
                if _in_window(q.flight_date, now, settings) and _try_alert(
                    db=db, source=source, notifier=notifier, quote=q, dest=dest,
                    seeds=seeds, settings=settings, now=now, pause=pause,
                ):
                    report.alerts_sent += 1
        items = plan_round(name, catalog, settings.origin, now.date(),
                           (settings.window_min_days, settings.window_max_days),
                           settings.revisit_days, db.last_scanned, now, _budget(settings, name))
        for item in items:
            pause()
            try:
                quotes = source.fetch_week(item.route, item.center)
            except SourceBlocked as exc:
                state = on_blocked(state, now, str(exc))
                break
            except SourceNetworkError as exc:
                state = on_network_error(state, str(exc))
                break
            except SourceError as exc:
                state = on_error(state, str(exc))
                continue
            db.add_quotes(quotes)
            db.mark_scanned(name, item.route, item.week_start, now)
            state = on_success(state)
            report.scanned += 1
            for q in quotes:
                if _in_window(q.flight_date, now, settings) and _try_alert(
                    db=db, source=source, notifier=notifier, quote=q, dest=dest_of[item.route],
                    seeds=seeds, settings=settings, now=now, pause=pause,
                ):
                    report.alerts_sent += 1
        db.save_state(state)

    for name in sources:
        state = db.get_state(name)
        if needs_health_notice(state) and notifier.send(format_health(state)):
            db.save_state(replace(state, notified=True))
    return report


def build_digest(*, db: Database, catalog: list[Destination], seeds: Mapping, settings: Settings,
                 now: datetime, source_names: Sequence[str] = ("smiles",)) -> str:
    since = now - timedelta(hours=DIGEST_LOOKBACK_HOURS)
    deals: list[tuple[Deal, Destination]] = []
    checked = 0
    for route, dest in routes(catalog, settings.origin):
        for name in source_names:
            quotes = db.latest_quotes(name, route, since)
            if quotes:
                checked += 1
            baseline = _baseline(db, seeds, name, route, now)
            for q in quotes:
                deal = _classify(q, baseline, settings) if _in_window(q.flight_date, now, settings) else None
                if deal is not None and deal.tier == "digest":
                    deals.append((deal, dest))
    return format_digest(deals, [db.get_state(n) for n in source_names], checked, now.date())
