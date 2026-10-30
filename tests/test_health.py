from dataclasses import replace
from datetime import timedelta

from conftest import T0
from fly.health import (
    is_available,
    needs_health_notice,
    on_blocked,
    on_error,
    on_network_error,
    on_success,
)
from fly.models import SourceState

OK = SourceState("smiles", "ok", None, 0, 0, None, False)


def test_blocked_backoff_doubles_and_caps():
    s = on_blocked(OK, T0, "403")
    assert s.status == "paused" and s.backoff_minutes == 60
    assert s.paused_until == T0 + timedelta(minutes=60)
    for _ in range(10):
        s = on_blocked(s, T0, "403")
    assert s.backoff_minutes == 1440
    assert not is_available(s, T0)
    assert is_available(s, T0 + timedelta(days=1, minutes=1))


def test_network_error_does_not_pause():
    s = on_network_error(OK, "dns")
    assert s.status == "ok" and s.failure_streak == 1 and is_available(s, T0)


def test_health_notice_once():
    s = on_error(on_error(on_error(OK, "parse"), "parse"), "parse")
    assert needs_health_notice(s) and s.last_error == "parse"
    assert not needs_health_notice(replace(s, notified=True))
    assert on_success(s).failure_streak == 0 and not on_success(s).notified


def test_success_clears_pause():
    s = on_success(on_blocked(OK, T0, "403"))
    assert s.status == "ok" and s.paused_until is None and s.backoff_minutes == 0
