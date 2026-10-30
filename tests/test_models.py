from datetime import datetime

from fly.models import FeedItem, PostDecision


def test_post_decision_holds_drop_reason():
    item = FeedItem("pontospravoar", "https://x/p", "Cartão", "", (), datetime(2026, 10, 29, 9, 0))
    d = PostDecision(item, "drop", "nao e passagem", None, None, None, None)
    assert (d.tier, d.reason, d.item.url) == ("drop", "nao e passagem", "https://x/p")
