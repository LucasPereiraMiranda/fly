from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fly.baseline import load_seeds
from fly.browser import BrowserSession
from fly.catalog import load_catalog
from fly.config import Settings, load_settings
from fly.db import Database
from fly.health import is_available
from fly.models import Route
from fly.notify.telegram import TelegramNotifier
from fly.run import build_digest, run_round
from fly.sources.smiles import CAROUSEL_MATCH, SmilesSource, build_search_url

log = logging.getLogger("fly")
LOG_FILE = Path("data/logs/fly.log")


def _setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])


def _open(settings: Settings) -> tuple[Database, TelegramNotifier]:
    if not settings.telegram_token or not settings.telegram_chat_id:
        raise SystemExit("missing FLY_TELEGRAM_API_KEY / FLY_TELEGRAM_CHAT_ID in .env")
    db = Database(settings.db_path)
    db.init()
    return db, TelegramNotifier(settings.telegram_token, settings.telegram_chat_id)


def cmd_run() -> None:
    settings = load_settings()
    db, notifier = _open(settings)
    now = datetime.now()
    if not is_available(db.get_state("smiles"), now):
        log.info("smiles paused until %s; nothing to do", db.get_state("smiles").paused_until)
        return
    with BrowserSession() as session:
        report = run_round(db=db, sources={"smiles": SmilesSource(session, datetime.now)},
                           notifier=notifier, catalog=load_catalog(), seeds=load_seeds(),
                           settings=settings, now=now)
    log.info("round done: scanned=%s alerts=%s skipped=%s",
             report.scanned, report.alerts_sent, report.skipped_sources)


def cmd_digest() -> None:
    settings = load_settings()
    db, notifier = _open(settings)
    text = build_digest(db=db, catalog=load_catalog(), seeds=load_seeds(), settings=settings,
                        now=datetime.now())
    log.info("digest sent=%s", notifier.send(text))


def capture_smiles(origin: str, destination: str, day: date, out: Path) -> None:
    """Save the raw public carousel JSON for one search, to be used as a test fixture."""
    with BrowserSession() as session:
        status, payload = session.fetch_json(build_search_url(Route(origin, destination), day), CAROUSEL_MATCH)
    if payload is None:
        raise SystemExit(f"no carousel response (HTTP {status})")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"saved {out} (HTTP {status})")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fly")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="scan due routes and send alerts")
    sub.add_parser("digest", help="send the daily summary")
    cap = sub.add_parser("capture-smiles", help="save a Smiles carousel response as a fixture")
    cap.add_argument("origin")
    cap.add_argument("destination")
    cap.add_argument("day", type=date.fromisoformat)
    cap.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    _setup_logging()
    if args.command == "run":
        cmd_run()
    elif args.command == "digest":
        cmd_digest()
    elif args.command == "capture-smiles":
        capture_smiles(args.origin, args.destination, args.day, args.out)


if __name__ == "__main__":
    main()
