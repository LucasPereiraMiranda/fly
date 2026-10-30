from __future__ import annotations

import argparse
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import httpx

from fly.baseline import load_seeds
from fly.catalog import load_catalog
from fly.config import Settings, load_settings
from fly.db import Database
from fly.feeds.reader import USER_AGENT
from fly.notify.telegram import TelegramNotifier
from fly.run import build_feed_digest, run_feeds

log = logging.getLogger("fly")
LOG_FILE = Path("data/logs/fly.log")


def _setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _open(settings: Settings) -> tuple[Database, TelegramNotifier]:
    if not settings.telegram_token or not settings.telegram_chat_id:
        raise SystemExit("missing FLY_TELEGRAM_API_KEY / FLY_TELEGRAM_CHAT_ID in .env")
    db = Database(settings.db_path)
    db.init()
    return db, TelegramNotifier(settings.telegram_token, settings.telegram_chat_id)


def cmd_run() -> None:
    settings = load_settings()
    db, notifier = _open(settings)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True) as client:
        report = run_feeds(db=db, client=client, notifier=notifier, catalog=load_catalog(),
                           seeds=load_seeds(), settings=settings, now=datetime.now())
    log.info("round done: new_posts=%s alerts=%s failed_feeds=%s",
             report.new_posts, report.alerts_sent, report.failed_feeds)


def cmd_digest() -> None:
    settings = load_settings()
    db, notifier = _open(settings)
    sent = notifier.send(build_feed_digest(db=db, settings=settings, now=datetime.now()))
    log.info("digest sent=%s", sent)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fly")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="read promo feeds and send alerts")
    sub.add_parser("digest", help="send the daily summary")
    args = parser.parse_args(argv)
    _setup_logging()
    if args.command == "run":
        cmd_run()
    else:
        cmd_digest()


if __name__ == "__main__":
    main()
