from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from fly.models import PostDecision, SourceState

SCHEMA = """
DROP TABLE IF EXISTS quotes;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS scan_cursor;
CREATE TABLE IF NOT EXISTS posts (
    url TEXT PRIMARY KEY,
    feed TEXT NOT NULL,
    title TEXT NOT NULL,
    published_at TEXT NOT NULL,
    seen_at TEXT NOT NULL,
    tier TEXT NOT NULL,
    reason TEXT NOT NULL,
    discount REAL,
    message TEXT,
    digest_line TEXT,
    sent INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS prices_seen (
    program TEXT NOT NULL,
    destination TEXT NOT NULL,
    miles INTEGER NOT NULL,
    seen_at TEXT NOT NULL
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
"""


def _dt(v: str | None) -> datetime | None:
    return datetime.fromisoformat(v) if v is not None else None


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)

    def init(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def post_seen(self, url: str) -> bool:
        return self._conn.execute("SELECT 1 FROM posts WHERE url = ?", (url,)).fetchone() is not None

    def record_post(self, decision: PostDecision, message: str | None, digest_line: str | None,
                    now: datetime) -> None:
        it = decision.item
        self._conn.execute(
            "INSERT OR REPLACE INTO posts"
            " (url, feed, title, published_at, seen_at, tier, reason, discount, message, digest_line)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (it.url, it.feed, it.title, it.published_at.isoformat(), now.isoformat(), decision.tier,
             decision.reason, decision.discount, message, digest_line),
        )
        self._conn.commit()

    def pending_alerts(self, now: datetime, max_age_hours: int) -> list[tuple[str, str]]:
        since = (now - timedelta(hours=max_age_hours)).isoformat()
        rows = self._conn.execute(
            "SELECT url, message FROM posts WHERE tier = 'alert' AND sent = 0 AND message IS NOT NULL"
            " AND published_at >= ? ORDER BY published_at",
            (since,),
        )
        return [(url, message) for url, message in rows]

    def mark_sent(self, url: str) -> None:
        self._conn.execute("UPDATE posts SET sent = 1 WHERE url = ?", (url,))
        self._conn.commit()

    def digest_lines(self, since: datetime) -> list[str]:
        rows = self._conn.execute(
            "SELECT digest_line FROM posts WHERE tier = 'digest' AND digest_line IS NOT NULL"
            " AND seen_at >= ? ORDER BY discount IS NULL, discount DESC, published_at DESC",
            (since.isoformat(),),
        )
        return [r[0] for r in rows]

    def add_price_seen(self, program: str, destination: str, miles: int, seen_at: datetime) -> None:
        self._conn.execute("INSERT INTO prices_seen VALUES (?, ?, ?, ?)",
                           (program, destination, miles, seen_at.isoformat()))
        self._conn.commit()

    def lowest_seen(self, program: str, destination: str) -> int | None:
        (low,) = self._conn.execute(
            "SELECT MIN(miles) FROM prices_seen WHERE program = ? AND destination = ?",
            (program, destination),
        ).fetchone()
        return low

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
            (state.name, state.status, state.paused_until.isoformat() if state.paused_until else None,
             state.backoff_minutes, state.failure_streak, state.last_error, int(state.notified)),
        )
        self._conn.commit()
