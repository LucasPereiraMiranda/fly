from decimal import Decimal
from pathlib import Path

from fly.config import load_settings
from fly.models import Route


def test_defaults_from_config(tmp_path):
    s = load_settings(Path("config/fly.toml"), tmp_path / "missing.env")
    assert s.origin == "CNF"
    assert (s.window_min_days, s.window_max_days) == (60, 240)
    assert (s.alert_discount, s.digest_discount) == (0.50, 0.30)
    assert (s.return_min_days, s.return_max_days) == (2, 30)
    assert s.milheiro_brl == {
        "smiles": Decimal("16.84"),
        "azul": Decimal("14.00"),
        "latam": Decimal("25.90"),
    }
    assert s.revisit_days == {"alta": 2, "media": 5, "baixa": 14}
    assert s.smiles_budget_per_round == 10
    assert s.smiles_delay_seconds == (8, 15)
    assert s.telegram_token is None


def test_env_secrets(tmp_path):
    env = tmp_path / ".env"
    env.write_text("FLY_TELEGRAM_API_KEY=abc\nFLY_TELEGRAM_CHAT_ID=42\n")
    s = load_settings(Path("config/fly.toml"), env)
    assert (s.telegram_token, s.telegram_chat_id) == ("abc", "42")


def test_route_reversed():
    assert Route("CNF", "MCZ").reversed() == Route("MCZ", "CNF")
