"""Global Bank's September and October 2026, as pure functions of (seed, scale factor, day).

Every table is drawn from its OWN random stream, seeded by (seed, table, day), so any day of any
source can be generated alone and comes out byte-identical every time. The one exception is the
core system's history (customers and accounts change over time, and a change needs the state it
changes): it is computed once per World, still from per-day streams, and cached.

The planted problems are the course's lessons (COURSE-PLAN.md, "The bank and its data"). Each one
is a named constant here and is asserted by `verify.py`, so a change to the generator cannot
quietly remove the bad batch Course 4 restores or the fraud ring Course 9 catches.

All people, merchants and numbers are synthetic. National ids and IBANs use formats no country
issues (an `XN` prefix; the unassigned country code `ZZ`), so nothing here is a real identifier.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from functools import cache

FIRST, LAST = date(2026, 9, 1), date(2026, 10, 31)
SETTLE_LAST = LAST + timedelta(days=3)  # clearing files keep arriving after month end (8.4)
CENT = Decimal('0.01')
HOME = 'EUR'

# --- scale ----------------------------------------------------------------------------------------
# At SF 1: 5,000 customers, ~6,500 accounts, ~5,500 card authorizations a day.
CUSTOMERS_PER_SF = 5_000
AUTHS_PER_CARD_DAY = 1.1
SAVINGS_SHARE = 0.3  # customers who also hold a savings account
FILE_MINUTES = 15  # the processor drops a card file every 15 minutes
APP_SESSIONS_PER_CUSTOMER_DAY = 0.15

# --- planted problems -----------------------------------------------------------------------------
BAD_BATCH = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)  # this file's amounts are in cents (4.1)
WALLET_FROM = date(2026, 10, 15)  # the processor adds `wallet_type` (3.5)
COMMA_FILE = datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc)  # a partner terminal sends "12,50" (3.6)
COMMA_ROWS = 3
RESEND_RATE = 0.003  # an authorization sent again, identical, in a later file (3.8)
LATE_RATE = 0.005  # an authorization that lands 1-6 hours late
DECLINE_RATE = 0.03
REVERSAL_RATE = 0.02  # approved, then reversed in the clearing file (4.6)
SETTLE_LAG = (1, 3)  # days from authorization to clearing (4.6, 8.4)
OUT_OF_ORDER = date(2026, 10, 9)  # two changes to one customer arrive in the wrong order (5.3)
ADDRESS_RATE = 0.002  # per customer per day
KYC_RATE = 0.001
CLOSE_RATE = 0.0003  # an account closes: op D (5.4)
NEW_CUSTOMER_RATE = 0.0004
ERASURE_DAY = date(2026, 10, 25)  # one customer asks to be erased (6.8)
# Card testing: (start, cards, authorizations per card), small amounts at online merchants the
# card has never used, inside ~15 minutes (9.1). September's rings come back as chargebacks: labels.
RINGS = [
    (datetime(2026, 9, 12, 3, 5, tzinfo=timezone.utc), 6, 10),
    (datetime(2026, 9, 26, 1, 40, tzinfo=timezone.utc), 5, 12),
    (datetime(2026, 10, 22, 2, 10, tzinfo=timezone.utc), 6, 11),
]
SKEW_MERCHANT = 'M0001'  # one supermarket chain, ~20% of authorizations (12.3)
SKEW_SHARE = 0.20
FOREIGN_SHARE = 0.08  # authorizations in another currency (8.2)
APP_VERSION_CHANGE = date(2026, 10, 8)  # the app goes 5.1 → 5.2, adding `device_os`

REGIONS = ['North', 'South', 'East', 'West', 'Central']
BRANCHES = [(f'B{r * 2 + i + 1:02d}', f'{region} {i + 1}', region) for r, region in enumerate(REGIONS) for i in range(2)]
SEGMENTS = [('standard', 70, (1800, 3200)), ('plus', 25, (3200, 6000)), ('premier', 5, (6000, 14000))]
KYC = ['VERIFIED', 'PENDING', 'REVIEW']
FIRST_NAMES = ['Ana', 'Ben', 'Chloe', 'Dev', 'Elena', 'Farid', 'Grace', 'Hugo', 'Ines', 'Jonas', 'Kofi', 'Lena', 'Mateo',
               'Nadia', 'Omar', 'Priya', 'Quinn', 'Rosa', 'Sami', 'Tara', 'Umar', 'Vera', 'Wen', 'Yusuf', 'Zoe']
LAST_NAMES = ['Adeyemi', 'Becker', 'Costa', 'Dubois', 'Eriksen', 'Fischer', 'Garcia', 'Haddad', 'Ivanova', 'Jansen',
              'Kowalski', 'Lopez', 'Moreau', 'Novak', 'Okafor', 'Petrov', 'Rossi', 'Schmidt', 'Tanaka', 'Weber']
STREETS = ['Mill Lane', 'Station Road', 'Harbour Street', 'Oak Avenue', 'Church Walk', 'Market Square', 'Elm Close',
           'River View', 'Park Road', 'Kings Row']
MCC = [('5411', 'Grocery stores'), ('5812', 'Restaurants'), ('5541', 'Fuel'), ('4111', 'Transport'),
       ('5311', 'Department stores'), ('5732', 'Electronics'), ('5999', 'Retail, other'), ('4814', 'Telecom'),
       ('5816', 'Digital goods'), ('5967', 'Direct marketing')]
MCC_W = [0, 22, 9, 12, 8, 5, 14, 4, 6, 3]  # the skewed supermarket is drawn separately
MERCHANT_WORDS = ['Corner', 'Harbour', 'Lumen', 'Brightway', 'Kestrel', 'Northgate', 'Oakline', 'Pebble', 'Riverside',
                  'Summit', 'Tidal', 'Vale']
MERCHANT_KINDS = {'5411': 'Grocer', '5812': 'Kitchen', '5541': 'Fuel', '4111': 'Transit', '5311': 'Stores',
                  '5732': 'Electronics', '5999': 'Goods', '4814': 'Mobile', '5816': 'Digital', '5967': 'Direct'}
ONLINE_MCC = {'5816', '5967', '4814'}
AMOUNT = {'5411': (4, 90), '5812': (8, 70), '5541': (30, 90), '4111': (2, 25), '5311': (15, 180), '5732': (20, 600),
          '5999': (5, 120), '4814': (10, 60), '5816': (1, 40), '5967': (5, 80)}
FX = {'USD': Decimal('1.0900'), 'GBP': Decimal('0.8600'), 'CHF': Decimal('0.9400')}  # per EUR, 1 September
CURRENCIES = list(FX)


def rng(seed: int, *key: object) -> random.Random:
    return random.Random(':'.join(str(k) for k in (seed, *key)))


def days(first: date = FIRST, last: date = LAST):
    d = first
    while d <= last:
        yield d
        d += timedelta(days=1)


def money(x: float) -> Decimal:
    return Decimal(str(x)).quantize(CENT)


def at(d: date, seconds: float) -> datetime:
    return datetime.combine(d, time(), timezone.utc) + timedelta(seconds=int(seconds))


def slot(t: datetime) -> datetime:
    """The 15-minute processor file a record arriving at `t` lands in."""
    return t.replace(minute=t.minute - t.minute % FILE_MINUTES, second=0, microsecond=0)


@dataclass(frozen=True)
class World:
    seed: int
    sf: float

    @property
    def n_customers(self) -> int:
        return max(200, round(CUSTOMERS_PER_SF * self.sf))

    # --- reference data -------------------------------------------------------------------------
    @cache
    def merchants(self) -> list[dict]:
        r = rng(self.seed, 'merchants')
        out = [{'merchant_id': SKEW_MERCHANT, 'name': 'FreshCo Supermarkets', 'mcc': '5411', 'country': 'XE', 'online': False}]
        n = max(60, round(400 * min(1.0, self.sf * 2)))
        for i in range(2, n + 1):
            mcc = r.choices([m for m, _ in MCC], MCC_W)[0]
            name = f'{r.choice(MERCHANT_WORDS)} {MERCHANT_KINDS[mcc]}'
            out.append({'merchant_id': f'M{i:04d}', 'name': name, 'mcc': mcc, 'country': 'XE', 'online': mcc in ONLINE_MCC})
        return out

    def fx_rates(self, d: date) -> list[dict]:
        out = []
        for ccy, base in FX.items():
            drift = rng(self.seed, 'fx', ccy, d).uniform(-0.004, 0.004) + 0.0002 * (d - FIRST).days * (1 if ccy == 'USD' else -1)
            out.append({'date': d.isoformat(), 'currency': ccy, 'per_eur': (base * Decimal(str(1 + drift))).quantize(Decimal('0.0001'))})
        return out

    # --- the core banking system: customers, accounts and cards, with their history --------------
    def _customer(self, r: random.Random, n: int, since: date) -> dict:
        first, last = r.choice(FIRST_NAMES), r.choice(LAST_NAMES)
        branch = r.choice(BRANCHES)
        segment = r.choices([s for s, _, _ in SEGMENTS], [w for _, w, _ in SEGMENTS])[0]
        return {'customer_id': f'C{n:06d}', 'first_name': first, 'last_name': last,
                'national_id': f'XN{r.randrange(10**8):08d}{r.choice("ABCDEFGHJK")}',
                'date_of_birth': date(r.randint(1950, 2006), r.randint(1, 12), r.randint(1, 28)).isoformat(),
                'email': f'{first.lower()}.{last.lower()}{n}@example.com',
                'address': f'{r.randint(1, 180)} {r.choice(STREETS)}', 'region': branch[2], 'branch_id': branch[0],
                'segment': segment, 'kyc_status': r.choices(KYC, [93, 5, 2])[0], 'customer_since': since.isoformat()}

    def _accounts_for(self, r: random.Random, c: dict, opened: date) -> list[dict]:
        n = int(c['customer_id'][1:])
        income = dict((s, rng_range) for s, _, rng_range in SEGMENTS)[c['segment']]
        out = [{'account_id': f'A{n:06d}1', 'customer_id': c['customer_id'], 'product': 'current',
                'iban': f'ZZ{n % 97:02d}GLBK{n:010d}01', 'opened': opened.isoformat(), 'status': 'OPEN',
                'overdraft_limit': {'standard': 500, 'plus': 1500, 'premier': 5000}[c['segment']],
                'opening_balance': money(r.uniform(-200, income[1] * 0.8))}]
        if r.random() < SAVINGS_SHARE:
            out.append({'account_id': f'A{n:06d}2', 'customer_id': c['customer_id'], 'product': 'savings',
                        'iban': f'ZZ{(n + 1) % 97:02d}GLBK{n:010d}02', 'opened': opened.isoformat(), 'status': 'OPEN',
                        'overdraft_limit': 0, 'opening_balance': money(r.uniform(500, income[1] * 6))})
        return out

    @cache
    def core_history(self) -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
        """Every change the core system records, in sequence order, plus the state on LAST.

        A change is (seq, ts, table, op, key, after). The first day is the initial snapshot: every
        customer and account as an insert. `seq` is the core system's own commit order; the order
        the CDC files ARRIVE in is decided in `cdc_files`.
        """
        changes: list[dict] = []
        customers: dict[str, dict] = {}
        accounts: dict[str, dict] = {}
        seq = 0

        def emit(t: datetime, table: str, op: str, key: dict, row: dict | None) -> None:
            nonlocal seq
            seq += 1
            changes.append({'seq': seq, 'ts': t, 'table': table, 'op': op, 'key': key, 'after': None if row is None else dict(row)})

        r = rng(self.seed, 'core', 'snapshot')
        for n in range(1, self.n_customers + 1):
            c = self._customer(r, n, date(r.randint(2004, 2025), r.randint(1, 12), 1))
            customers[c['customer_id']] = c
            emit(at(FIRST, 60), 'customers', 'I', {'customer_id': c['customer_id']}, c)
            for a in self._accounts_for(r, c, date.fromisoformat(c['customer_since'])):
                accounts[a['account_id']] = a
                emit(at(FIRST, 60), 'accounts', 'I', {'account_id': a['account_id']}, a)
        next_id = self.n_customers + 1
        for d in days(FIRST + timedelta(days=1), LAST):
            r = rng(self.seed, 'core', d)
            ids = sorted(customers)
            moves = [cid for cid in ids if r.random() < ADDRESS_RATE]
            if d == OUT_OF_ORDER:  # one customer moves twice in a day: the second change arrives first
                moves = [m for m in moves if m != ids[0]] + [ids[0], ids[0]]
            for cid in moves:
                c = customers[cid]
                branch = r.choice(BRANCHES)
                c.update(address=f'{r.randint(1, 180)} {r.choice(STREETS)}', region=branch[2], branch_id=branch[0])
                emit(at(d, r.uniform(8 * 3600, 20 * 3600)), 'customers', 'U', {'customer_id': cid}, c)
            for cid in ids:
                if r.random() < KYC_RATE:
                    c = customers[cid]
                    c['kyc_status'] = r.choice([k for k in KYC if k != c['kyc_status']])
                    emit(at(d, r.uniform(9 * 3600, 17 * 3600)), 'customers', 'U', {'customer_id': cid}, c)
            for aid in sorted(accounts):
                a = accounts[aid]
                if a['status'] == 'OPEN' and a['product'] == 'savings' and r.random() < CLOSE_RATE:
                    del accounts[aid]
                    emit(at(d, r.uniform(9 * 3600, 17 * 3600)), 'accounts', 'D', {'account_id': aid}, None)
            for _ in range(sum(1 for _ in range(len(ids)) if r.random() < NEW_CUSTOMER_RATE)):
                c = self._customer(r, next_id, d)
                next_id += 1
                customers[c['customer_id']] = c
                t = at(d, r.uniform(9 * 3600, 17 * 3600))
                emit(t, 'customers', 'I', {'customer_id': c['customer_id']}, c)
                for a in self._accounts_for(r, c, d):
                    accounts[a['account_id']] = a
                    emit(t, 'accounts', 'I', {'account_id': a['account_id']}, a)
        changes.sort(key=lambda ch: (ch['ts'], ch['seq']))
        for i, ch in enumerate(changes, 1):  # seq is commit order: renumber by time
            ch['seq'] = i
        return changes, customers, accounts

    def cdc_files(self, d: date) -> dict[str, list[dict]]:
        """The CDC tool's files for day d, by name, in ARRIVAL order: one at 12:00, one at 23:59.

        On OUT_OF_ORDER, a customer's two changes of the day are split across the files the wrong
        way round: the later change (higher seq) arrives in the first file.
        """
        todays = [ch for ch in self.core_history()[0] if ch['ts'].date() == d]
        noon = at(d, 12 * 3600)
        early, late = [ch for ch in todays if ch['ts'] < noon], [ch for ch in todays if ch['ts'] >= noon]
        if d == OUT_OF_ORDER:
            pair = self.out_of_order_pair()
            early = [ch for ch in early if ch['seq'] not in pair] + [ch for ch in todays if ch['seq'] == max(pair)]
            late = [ch for ch in late if ch['seq'] not in pair] + [ch for ch in todays if ch['seq'] == min(pair)]
        return {name: rows for name, rows in (('changes-1200.json', early), ('changes-2359.json', late)) if rows}

    def out_of_order_pair(self) -> tuple[int, int]:
        moved = [ch for ch in self.core_history()[0] if ch['ts'].date() == OUT_OF_ORDER and ch['table'] == 'customers' and ch['op'] == 'U']
        first_id = min(int(ch['key']['customer_id'][1:]) for ch in moved)
        seqs = sorted(ch['seq'] for ch in moved if ch['key']['customer_id'] == f'C{first_id:06d}')
        return seqs[0], seqs[1]

    @cache
    def cards(self) -> list[dict]:
        """One debit card per current account that exists on FIRST (card ids are tokens, never PANs)."""
        changes = self.core_history()[0]
        current = [ch['after'] for ch in changes if ch['table'] == 'accounts' and ch['op'] == 'I' and ch['after']['product'] == 'current']
        return [{'card_id': f'K{a["account_id"][1:7]}', 'account_id': a['account_id'], 'customer_id': a['customer_id'],
                 'since': a['opened']} for a in current]

    # --- card authorizations ------------------------------------------------------------------------
    def _auth(self, r: random.Random, card: dict, merchant: dict, t: datetime, amount: Decimal | None = None) -> dict:
        lo, hi = AMOUNT[merchant['mcc']]
        foreign = merchant['merchant_id'] != SKEW_MERCHANT and r.random() < FOREIGN_SHARE
        a = {'auth_id': f'au-{r.getrandbits(48):012x}', 'card_id': card['card_id'], 'merchant_id': merchant['merchant_id'],
             'mcc': merchant['mcc'], 'amount': amount if amount is not None else money(r.uniform(lo, hi)),
             'currency': r.choice(CURRENCIES) if foreign else HOME, 'auth_ts': t,
             'entry_mode': 'online' if merchant['online'] else r.choices(['contactless', 'chip'], [70, 30])[0],
             'status': 'DECLINED' if r.random() < DECLINE_RATE else 'APPROVED'}
        return a

    @cache
    def auths_on(self, d: date) -> tuple[dict, ...]:
        """Every authorization made on day d, in time order (fraud rings included)."""
        r = rng(self.seed, 'auths', d)
        cards = [c for c in self.cards() if date.fromisoformat(c['since']) <= d]
        merchants = self.merchants()
        others = merchants[1:]
        out: list[dict] = []
        weekend = d.weekday() >= 5
        n = round(len(cards) * AUTHS_PER_CARD_DAY * (1.15 if weekend else 1.0))
        for _ in range(n):
            card = r.choice(cards)
            merchant = merchants[0] if r.random() < SKEW_SHARE else r.choice(others)
            seconds = max(0.0, min(86399.0, r.gauss(14.5 * 3600, 4.2 * 3600)))
            out.append(self._auth(r, card, merchant, at(d, seconds)))
        for start, n_cards, per_card in RINGS:
            if start.date() != d:
                continue
            rr = rng(self.seed, 'ring', start.isoformat())
            online = [m for m in others if m['online']]
            for card in rr.sample(cards, n_cards):
                for k in range(per_card):
                    t = start + timedelta(seconds=rr.uniform(0, 14 * 60))
                    a = self._auth(rr, card, rr.choice(online), t, money(rr.uniform(0.5, 2.0)))
                    a.update(currency=HOME, entry_mode='online', status='DECLINED' if rr.random() < 0.35 else 'APPROVED')
                    a['ring'] = start.isoformat()  # never written to a file: the ground truth for verify/labels
                    out.append(a)
        out.sort(key=lambda a: (a['auth_ts'], a['auth_id']))
        return tuple(out)

    def ring_auths(self, start: datetime) -> list[dict]:
        return [a for a in self.auths_on(start.date()) if a.get('ring') == start.isoformat()]

    @cache
    def _arrivals(self, d: date) -> tuple[tuple[datetime, dict], ...]:
        """(arrival time, authorization) for everything the processor sent on day d: made on d or the
        day before, a few minutes after it happened; some hours late; a few sent twice."""
        out = []
        for made in (d - timedelta(days=1), d):
            if made < FIRST:
                continue
            r = rng(self.seed, 'arrive', made)
            for a in self.auths_on(made):
                late = r.random() < LATE_RATE
                arrived = a['auth_ts'] + timedelta(seconds=r.uniform(3600, 6 * 3600) if late else r.uniform(20, 180))
                resend = r.random() < RESEND_RATE
                again = arrived + timedelta(seconds=r.uniform(1800, 4 * 3600))
                for t in [arrived] + ([again] if resend else []):
                    if t.date() == d:
                        out.append((t, a))
        out.sort(key=lambda p: (p[0], p[1]['auth_id']))
        return tuple(out)

    def card_files(self, d: date) -> dict[datetime, list[dict]]:
        files: dict[datetime, list[dict]] = {}
        for t, a in self._arrivals(d):
            files.setdefault(slot(t), []).append(a)
        return files

    # --- clearing: settlements and reversals -------------------------------------------------------
    def settlements_on(self, d: date) -> list[dict]:
        out = []
        for back in range(SETTLE_LAG[0], SETTLE_LAG[1] + 1):
            made = d - timedelta(days=back)
            if not FIRST <= made <= LAST:
                continue
            r = rng(self.seed, 'clear', made)
            rates = {x['currency']: x['per_eur'] for x in self.fx_rates(made)}
            for a in self.auths_on(made):
                lag = r.randint(*SETTLE_LAG)
                reversed_ = r.random() < REVERSAL_RATE
                if a['status'] != 'APPROVED' or lag != back:
                    continue
                eur = a['amount'] if a['currency'] == HOME else (a['amount'] / rates[a['currency']]).quantize(CENT)
                out.append({'auth_id': a['auth_id'], 'card_id': a['card_id'], 'kind': 'REVERSAL' if reversed_ else 'SETTLEMENT',
                            'amount': a['amount'], 'currency': a['currency'], 'amount_eur': Decimal('0.00') if reversed_ else eur,
                            'cleared_date': d.isoformat()})
        out.sort(key=lambda s: s['auth_id'])
        return out

    def chargebacks(self) -> list[dict]:
        """Confirmed card-testing fraud from September's rings: the labels Course 9 trains on."""
        return [{'auth_id': a['auth_id'], 'card_id': a['card_id'], 'reported': (start.date() + timedelta(days=9)).isoformat(),
                 'reason': 'card_testing'}
                for start, _, _ in RINGS if start.date() < date(2026, 10, 1) for a in self.ring_auths(start)]

    # --- postings: the core system's non-card movements --------------------------------------------
    def postings_on(self, d: date) -> list[dict]:
        r = rng(self.seed, 'postings', d)
        out = []
        accounts = [ch['after'] for ch in self.core_history()[0] if ch['table'] == 'accounts' and ch['op'] == 'I'
                    and date.fromisoformat(ch['after']['opened']) <= d]
        income = {s: rr for s, _, rr in SEGMENTS}
        segment = {ch['after']['customer_id']: ch['after']['segment'] for ch in self.core_history()[0]
                   if ch['table'] == 'customers' and ch['op'] == 'I'}
        for a in accounts:
            if a['product'] != 'current':
                continue
            seg = segment[a['customer_id']]
            ar = rng(self.seed, 'salary', a['account_id'])
            if d.day == 25:
                out.append(('SALARY', a, money(ar.uniform(*income[seg]))))
            if d.day == 1:
                out.append(('RENT', a, -money(ar.uniform(0.25, 0.4) * income[seg][0])))
            if r.random() < 0.03:
                out.append(('TRANSFER', a, money(r.uniform(-400, 300))))
        return [{'posting_id': f'P{d:%Y%m%d}{i:06d}', 'account_id': a['account_id'], 'kind': kind, 'amount': amt,
                 'currency': HOME, 'posted_date': d.isoformat()} for i, (kind, a, amt) in enumerate(out, 1)]

    # --- the mobile app ------------------------------------------------------------------------------
    def app_events_on(self, d: date) -> list[dict]:
        r = rng(self.seed, 'app', d)
        ids = [f'C{n:06d}' for n in range(1, self.n_customers + 1)]
        out = []
        for _ in range(round(len(ids) * APP_SESSIONS_PER_CUSTOMER_DAY)):
            cid = r.choice(ids)
            sid = f's-{r.getrandbits(40):010x}'
            t = at(d, max(0.0, min(86000.0, r.gauss(13 * 3600, 5 * 3600))))
            os_ = r.choice(['ios', 'android'])
            for ev in ['login', *r.sample(['view_balance', 'view_card', 'transfer', 'card_freeze', 'statement'], r.randint(1, 3))]:
                e = {'session_id': sid, 'customer_id': cid, 'event': ev, 'ts': t,
                     'app_version': '5.2.0' if d >= APP_VERSION_CHANGE else '5.1.3'}
                if d >= APP_VERSION_CHANGE:
                    e['device_os'] = os_
                out.append(e)
                t += timedelta(seconds=r.uniform(5, 90))
        out.sort(key=lambda e: (e['ts'], e['session_id']))
        return out

    # --- the privacy team ----------------------------------------------------------------------------
    def erasure_requests(self) -> list[dict]:
        r = rng(self.seed, 'erasure')
        cid = f'C{r.randint(1, self.n_customers):06d}'
        return [{'request_id': 'ER-2026-0031', 'customer_id': cid, 'received': at(ERASURE_DAY, 10 * 3600 + 1234),
                 'basis': 'erasure request (illustrative)'}]
