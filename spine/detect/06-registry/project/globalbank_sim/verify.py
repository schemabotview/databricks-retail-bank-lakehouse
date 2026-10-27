"""Assert every planted problem (COURSE-PLAN.md, "The bank and its data") is really in the data.

A lesson is built on each of these; a generator change that loses one fails here, not on screen.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta

from .__main__ import auth_record
from .model import (BAD_BATCH, COMMA_FILE, ERASURE_DAY, FOREIGN_SHARE, OUT_OF_ORDER, RINGS, SKEW_MERCHANT, SKEW_SHARE,
                    WALLET_FROM, World, days)

OCTOBER = list(days(date(2026, 10, 1), date(2026, 10, 31)))


def verify(world: World) -> int:
    problems: list[str] = []
    ok: list[str] = []

    def check(cond: bool, good: str, bad: str) -> None:
        (ok if cond else problems).append(good if cond else bad)

    bad = world.card_files(BAD_BATCH.date()).get(BAD_BATCH, [])
    cents = [json.loads(auth_record(world, a, BAD_BATCH, i))['amount'] for i, a in enumerate(bad)]
    check(bool(cents) and all(isinstance(c, int) and c == int(a['amount'] * 100) for c, a in zip(cents, bad)),
          f'bad batch {BAD_BATCH:%Y-%m-%d %H:%M}: {len(cents)} authorizations in cents (×100)', 'the bad batch is not in cents')

    before = json.loads(auth_record(world, world.auths_on(WALLET_FROM - timedelta(days=1))[0], BAD_BATCH.replace(day=14, hour=0), 0))
    after_slot = min(world.card_files(WALLET_FROM))
    after = json.loads(auth_record(world, world.card_files(WALLET_FROM)[after_slot][0], after_slot, 0))
    check('wallet_type' not in before and 'wallet_type' in after, f'schema change on {WALLET_FROM}: + wallet_type',
          'wallet_type does not appear on its day')

    comma = [json.loads(auth_record(world, a, COMMA_FILE, i))['amount'] for i, a in enumerate(world.card_files(COMMA_FILE.date())[COMMA_FILE])]
    strings = [c for c in comma if isinstance(c, str)]
    check(bool(strings) and all(',' in s for s in strings), f'partner file {COMMA_FILE:%Y-%m-%d %H:%M}: amounts {", ".join(strings)}',
          'no "12,50" amounts in the partner file')

    arrived = [a['auth_id'] for d in OCTOBER[:7] for _, a in world._arrivals(d)]
    resent = sum(1 for n in Counter(arrived).values() if n > 1)
    late = sum(1 for d in OCTOBER[:7] for t, a in world._arrivals(d) if (t - a['auth_ts']).total_seconds() > 3600)
    check(resent > 0, f'resends: {resent} authorizations sent twice in a week', 'no resent authorizations')
    check(late > 0, f'late: {late} authorizations land over an hour late in a week', 'no late authorizations')

    week = [a for d in OCTOBER[:7] for a in world.auths_on(d)]
    skew = sum(1 for a in week if a['merchant_id'] == SKEW_MERCHANT) / len(week)
    check(abs(skew - SKEW_SHARE) < 0.03, f'skew: {SKEW_MERCHANT} is {skew:.1%} of authorizations', f'{SKEW_MERCHANT} is {skew:.1%}, not ~{SKEW_SHARE:.0%}')
    foreign = Counter(a['currency'] for a in week if a['currency'] != 'EUR')
    share = sum(foreign.values()) / len(week)
    check(len(foreign) == 3 and abs(share - FOREIGN_SHARE * (1 - SKEW_SHARE)) < 0.03,
          f'foreign spend: {share:.1%} in {", ".join(sorted(foreign))}', f'foreign spend is {share:.1%} in {sorted(foreign)}')

    settled = [s for d in days(date(2026, 10, 2), date(2026, 10, 8)) for s in world.settlements_on(d)]
    lags = Counter((date.fromisoformat(s['cleared_date']) - next(a['auth_ts'].date() for a in [lookup(world, s)])).days for s in settled[:400])
    reversals = sum(1 for s in settled if s['kind'] == 'REVERSAL')
    check(set(lags) == {1, 2, 3}, f'clearing lags: {dict(sorted(lags.items()))} days (first 400)', f'clearing lags are {dict(lags)}')
    check(reversals > 0, f'reversals: {reversals} in a week of clearing', 'no reversals')
    nov = world.settlements_on(date(2026, 11, 2))
    check(any(s for s in nov), f'clearing after month end: {len(nov)} October authorizations clear on 2 November',
          'nothing clears after October')

    lo, hi = world.out_of_order_pair()
    files = world.cdc_files(OUT_OF_ORDER)
    first_file = [ch['seq'] for ch in next(iter(files.values()))]
    check(hi in first_file and lo not in first_file, f'out of order on {OUT_OF_ORDER}: seq {hi} arrives before seq {lo}',
          'no out-of-order CDC pair')
    ops = Counter(ch['op'] for ch in world.core_history()[0])
    check(ops['D'] > 0 and ops['U'] > 0, f'core changes: {ops["I"]:,} inserts, {ops["U"]} updates, {ops["D"]} deletes',
          f'core changes lack updates or deletes: {dict(ops)}')

    for start, n_cards, per_card in RINGS:
        ring = world.ring_auths(start)
        span = (max(a['auth_ts'] for a in ring) - min(a['auth_ts'] for a in ring)).total_seconds() / 60
        cards = {a['card_id'] for a in ring}
        check(len(cards) == n_cards and len(ring) == n_cards * per_card and span < 15 and all(a['amount'] <= 2 for a in ring),
              f'card testing {start:%Y-%m-%d %H:%M}: {len(cards)} cards, {len(ring)} authorizations ≤ 2.00 in {span:.0f} min',
              f'the ring at {start} is not as planted')
    labels = world.chargebacks()
    check(len(labels) == sum(n * k for s, n, k in RINGS if s.month == 9), f'labels: {len(labels)} September chargebacks',
          'the chargebacks do not match September\'s rings')

    er = world.erasure_requests()
    check(er[0]['received'].date() == ERASURE_DAY, f'erasure request: {er[0]["customer_id"]} on {ERASURE_DAY}', 'no erasure request')

    for line in ok:
        print(f'✓ {line}')
    for line in problems:
        print(f'✗ {line}')
    return 1 if problems else 0


def lookup(world: World, s: dict) -> dict:
    """The authorization a clearing row settles (searched over the three days before it)."""
    d = date.fromisoformat(s['cleared_date'])
    for back in range(1, 4):
        for a in world.auths_on(d - timedelta(days=back)):
            if a['auth_id'] == s['auth_id']:
                return a
    raise KeyError(s['auth_id'])
