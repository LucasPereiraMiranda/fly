from datetime import datetime

import pytest

from fly.models import FeedItem

T0 = datetime(2026, 9, 1, 10, 0)


@pytest.fixture
def db(tmp_path):
    from fly.db import Database

    d = Database(tmp_path / "t.db")
    d.init()
    return d


def item(title: str, summary: str = "", feed: str = "pontospravoar", published_at: datetime = T0,
         url: str | None = None) -> FeedItem:
    return FeedItem(feed, url or f"https://example.test/{abs(hash(title))}", title, summary, (), published_at)
