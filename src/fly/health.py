from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from fly.models import SourceState

FIRST_BACKOFF_MINUTES = 60
MAX_BACKOFF_MINUTES = 1440


def on_success(s: SourceState) -> SourceState:
    return replace(s, status="ok", paused_until=None, backoff_minutes=0, failure_streak=0,
                   last_error=None, notified=False)


def on_blocked(s: SourceState, now: datetime, detail: str) -> SourceState:
    """The site refused us (anti-bot): pause with a backoff that doubles up to a day."""
    backoff = FIRST_BACKOFF_MINUTES if s.backoff_minutes == 0 else s.backoff_minutes * 2
    backoff = min(backoff, MAX_BACKOFF_MINUTES)
    return replace(s, status="paused", paused_until=now + timedelta(minutes=backoff),
                   backoff_minutes=backoff, failure_streak=s.failure_streak + 1, last_error=detail)


def on_network_error(s: SourceState, detail: str) -> SourceState:
    """Our own connectivity failed (Mac offline/asleep): count it, but never pause the source."""
    return replace(s, failure_streak=s.failure_streak + 1, last_error=detail)


def on_error(s: SourceState, detail: str) -> SourceState:
    return replace(s, failure_streak=s.failure_streak + 1, last_error=detail)


def is_available(s: SourceState, now: datetime) -> bool:
    return s.status == "ok" or (s.paused_until is not None and now >= s.paused_until)


def needs_health_notice(s: SourceState, threshold: int = 3) -> bool:
    return s.failure_streak >= threshold and not s.notified
