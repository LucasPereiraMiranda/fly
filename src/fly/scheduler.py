from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fly.catalog import PRIORITIES, Destination, routes
from fly.models import Route

WEEK = timedelta(days=7)


@dataclass(frozen=True)
class WorkItem:
    source: str
    route: Route
    week_start: date

    @property
    def center(self) -> date:
        """The date to search for: the site's 7-day carousel is centered on it."""
        return self.week_start + timedelta(days=3)


def plan_round(
    source: str,
    catalog: list[Destination],
    origin: str,
    today: date,
    window: tuple[int, int],
    revisit_days: Mapping[str, int],
    last_scanned: Callable[[str, Route, date], datetime | None],
    now: datetime,
    budget: int,
) -> list[WorkItem]:
    """Route-weeks due for a scan, most urgent first, capped at the round's budget.

    Never-scanned items come first (higher priority, nearer week, outbound first);
    then items ordered by how overdue they are relative to their priority's interval.
    """
    weeks = []
    week = today + timedelta(days=window[0])
    while week <= today + timedelta(days=window[1]):
        weeks.append(week)
        week += WEEK

    ranked = []
    for route, dest in routes(catalog, origin):
        rank = PRIORITIES.index(dest.priority)
        direction = 0 if route.origin == origin else 1
        interval = timedelta(days=revisit_days[dest.priority])
        for week_start in weeks:
            last = last_scanned(source, route, week_start)
            item = WorkItem(source, route, week_start)
            if last is None:
                ranked.append(((0, 0.0, rank, week_start, direction), item))
            elif now - last >= interval:
                overdue = (now - last) / interval
                ranked.append(((1, -overdue, rank, week_start, direction), item))
    ranked.sort(key=lambda pair: pair[0])
    return [item for _, item in ranked[:budget]]
