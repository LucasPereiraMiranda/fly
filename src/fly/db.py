from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fly.models import FareQuote, Route, SourceState

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    source TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    flight_date TEXT NOT NULL,
    miles INTEGER,
    cash_brl TEXT,
    taxes_brl TEXT,
    observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS quotes_route ON quotes (source, origin, destination, observed_at);
CREATE TABLE IF NOT EXISTS alerts (
    key TEXT PRIMARY KEY,
    value REAL NOT NULL,
    sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_state (
    name TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    paused_until TEXT,
    backoff_minutes INTEGER NOT NULL,
    failure_streak INTEGER NOT NULL,
    last_error TEXT,
    notified INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS scan_cursor (
    source TEXT NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    week_start TEXT NOT NULL,
    scanned_at TEXT NOT NULL,
    PRIMARY KEY (source, origin, destination, week_start)
);
"""


def _dec(v: str | None) -> Decimal | None:
    return Decimal(v) if v is not None else None


def _dt(v: str | None) -> datetime | None:
    return datetime.fromisoformat(v) if v is not None else None


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)

    def init(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def add_quotes(self, quotes: Iterable[FareQuote]) -> None:
        self._conn.executemany(
            "INSERT INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    q.source, q.route.origin, q.route.destination, q.flight_date.isoformat(),
                    q.miles,
                    str(q.cash_brl) if q.cash_brl is not None else None,
                    str(q.taxes_brl) if q.taxes_brl is not None else None,
                    q.observed_at.isoformat(),
                )
                for q in quotes
            ],
        )
        self._conn.commit()

    def daily_lows(self, source: str, route: Route, since: datetime) -> list[float]:
        rows = self._conn.execute(
            "SELECT MIN(miles) FROM quotes WHERE source = ? AND origin = ? AND destination = ?"
            " AND observed_at >= ? AND miles > 0 GROUP BY flight_date",
            (source, route.origin, route.destination, since.isoformat()),
        )
        return [float(r[0]) for r in rows]

    def scan_days(self, source: str, route: Route, since: datetime) -> int:
        (n,) = self._conn.execute(
            "SELECT COUNT(DISTINCT substr(observed_at, 1, 10)) FROM quotes"
            " WHERE source = ? AND origin = ? AND destination = ? AND observed_at >= ?",
            (source, route.origin, route.destination, since.isoformat()),
        ).fetchone()
        return n

    def latest_quotes(self, source: str, route: Route, since: datetime) -> list[FareQuote]:
        rows = self._conn.execute(
            "SELECT q.flight_date, q.miles, q.cash_brl, q.taxes_brl, q.observed_at FROM quotes q"
            " JOIN (SELECT flight_date, MAX(observed_at) AS last FROM quotes"
            "       WHERE source = ? AND origin = ? AND destination = ? AND observed_at >= ?"
            "       GROUP BY flight_date) m"
            " ON q.flight_date = m.flight_date AND q.observed_at = m.last"
            " WHERE q.source = ? AND q.origin = ? AND q.destination = ?"
            " ORDER BY q.flight_date",
            (source, route.origin, route.destination, since.isoformat(),
             source, route.origin, route.destination),
        )
        latest: dict[str, FareQuote] = {}
        for fd, miles, cash, taxes, obs in rows:
            # Several rows can share the latest timestamp; keep the cheapest one per date.
            q = FareQuote(source, route, date.fromisoformat(fd), miles, _dec(cash), _dec(taxes),
                          datetime.fromisoformat(obs))
            kept = latest.get(fd)
            if kept is None or (q.miles or 0) < (kept.miles or 0):
                latest[fd] = q
        return list(latest.values())

    def last_alert_value(self, key: str) -> float | None:
        row = self._conn.execute("SELECT value FROM alerts WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def record_alert(self, key: str, value: float, sent_at: datetime) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO alerts VALUES (?, ?, ?)", (key, value, sent_at.isoformat())
        )
        self._conn.commit()

    def get_state(self, name: str) -> SourceState:
        row = self._conn.execute(
            "SELECT status, paused_until, backoff_minutes, failure_streak, last_error, notified"
            " FROM source_state WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return SourceState(name, "ok", None, 0, 0, None, False)
        status, paused_until, backoff, streak, last_error, notified = row
        return SourceState(name, status, _dt(paused_until), backoff, streak, last_error, bool(notified))

    def save_state(self, state: SourceState) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO source_state VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                state.name, state.status,
                state.paused_until.isoformat() if state.paused_until else None,
                state.backoff_minutes, state.failure_streak, state.last_error, int(state.notified),
            ),
        )
        self._conn.commit()

    def last_scanned(self, source: str, route: Route, week_start: date) -> datetime | None:
        row = self._conn.execute(
            "SELECT scanned_at FROM scan_cursor"
            " WHERE source = ? AND origin = ? AND destination = ? AND week_start = ?",
            (source, route.origin, route.destination, week_start.isoformat()),
        ).fetchone()
        return _dt(row[0]) if row else None

    def mark_scanned(self, source: str, route: Route, week_start: date, at: datetime) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO scan_cursor VALUES (?, ?, ?, ?, ?)",
            (source, route.origin, route.destination, week_start.isoformat(), at.isoformat()),
        )
        self._conn.commit()
