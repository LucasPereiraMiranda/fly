from fly.detect import discount_tier
from fly.models import Baseline

NORMAL = Baseline(35000, "miles", False)


def test_maceio_8k_is_alert():
    discount, tier = discount_tier(8000, NORMAL, 0.5, 0.3)
    assert tier == "alert" and round(discount, 3) == 0.771


def test_digest_band():
    assert discount_tier(21000, NORMAL, 0.5, 0.3)[1] == "digest"


def test_small_discount_has_no_tier():
    assert discount_tier(30000, NORMAL, 0.5, 0.3)[1] is None


def test_non_positive_price():
    assert discount_tier(0, NORMAL, 0.5, 0.3) == (0.0, None)
