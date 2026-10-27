"""One integration test: the same transform, on the workspace's real silver."""
from globalbank.session import get_spark
from globalbank.transforms import velocity


def test_velocity_finds_the_october_ring():
    auths = get_spark().table('globalbank_dev.silver.card_transactions') \
        .where("to_date(auth_ts) = '2026-10-22'")
    flagged = velocity(auths).where('auths_10m > 5')
    cards = {r.card_id for r in flagged.select('card_id').distinct().collect()}
    assert len(cards) == 6  # the 22 October ring: six cards
