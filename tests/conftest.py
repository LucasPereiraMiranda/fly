from datetime import datetime

import pytest

T0 = datetime(2026, 9, 1, 10, 0)


@pytest.fixture
def db(tmp_path):
    from fly.db import Database

    d = Database(tmp_path / "t.db")
    d.init()
    return d
