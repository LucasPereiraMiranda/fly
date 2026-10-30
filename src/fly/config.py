from __future__ import annotations

import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    origin: str
    window_min_days: int
    window_max_days: int
    alert_discount: float
    digest_discount: float
    post_max_age_hours: int
    milheiro_brl: dict[str, Decimal]
    feeds: dict[str, str]
    db_path: Path
    telegram_token: str | None
    telegram_chat_id: str | None


def load_settings(
    config_path: Path = Path("config/fly.toml"),
    env_path: Path = Path(".env"),
) -> Settings:
    with config_path.open("rb") as f:
        cfg = tomllib.load(f)
    env = dotenv_values(env_path) if env_path.exists() else {}
    return Settings(
        origin=cfg["origin"],
        window_min_days=cfg["window_min_days"],
        window_max_days=cfg["window_max_days"],
        alert_discount=cfg["alert_discount"],
        digest_discount=cfg["digest_discount"],
        post_max_age_hours=cfg["post_max_age_hours"],
        milheiro_brl={k: Decimal(v) for k, v in cfg["milheiro_brl"].items()},
        feeds=dict(cfg["feeds"]),
        db_path=Path(cfg["db_path"]),
        telegram_token=env.get("FLY_TELEGRAM_API_KEY") or None,
        telegram_chat_id=env.get("FLY_TELEGRAM_CHAT_ID") or None,
    )
