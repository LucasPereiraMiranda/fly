from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from fly.browser import BrowserSession
from fly.models import Route
from fly.sources.smiles import CAROUSEL_MATCH, build_search_url


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
    cap = sub.add_parser("capture-smiles", help="save a Smiles carousel response as a fixture")
    cap.add_argument("origin")
    cap.add_argument("destination")
    cap.add_argument("day", type=date.fromisoformat)
    cap.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "capture-smiles":
        capture_smiles(args.origin, args.destination, args.day, args.out)


if __name__ == "__main__":
    main()
