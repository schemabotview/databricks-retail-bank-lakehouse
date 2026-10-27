"""Write Global Bank's sources as its systems and vendors deliver them: the landing zone.

  python -m globalbank_sim --out landing                        September and October, every source
  python -m globalbank_sim --out landing --from 2026-10-01 --to 2026-10-01 --only card_auths
  python -m globalbank_sim stats --out landing                  what landed: files and records
  python -m globalbank_sim verify                               assert every planted problem

Same seed and SF → byte-identical files. Layout under --out:

  card_auths/<day>/auths-<hhmm>.json    the card processor: JSON lines, a file every 15 minutes
  settlements/settlements-<day>.csv     the scheme's clearing file, 1-3 days after the authorization
  core_cdc/<day>/changes-<hhmm>.json    the CDC tool on the core banking system: JSON lines
  postings/postings-<day>.csv           the core system's non-card movements: salary, rent, transfers
  app_events/<day>/events-<hh>.json     the mobile app's telemetry, hourly
  fx_rates/fx-<day>.csv                 daily rates, per EUR
  reference/merchants.csv, mcc.csv, branches.csv
  chargebacks/chargebacks-2026-09.csv   confirmed fraud: September's labels
  privacy/erasure-requests-2026-10.csv  the privacy team's requests
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from .model import (BAD_BATCH, BRANCHES, COMMA_FILE, COMMA_ROWS, FIRST, LAST, MCC, SETTLE_LAST, WALLET_FROM, World,
                    days, rng)

SOURCES = ['card_auths', 'settlements', 'core_cdc', 'postings', 'app_events', 'fx_rates', 'reference', 'chargebacks',
           'privacy']


def iso(t: datetime) -> str:
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def jvalue(v) -> str:
    if isinstance(v, Decimal):
        return str(v)  # a JSON number with its two decimals, never a float's repr
    if isinstance(v, datetime):
        return json.dumps(iso(v))
    if isinstance(v, dict):
        return jline(v)  # a CDC record's key and after-image
    return json.dumps(v)


def jline(row: dict) -> str:
    return '{' + ','.join(f'{json.dumps(k)}:{jvalue(v)}' for k, v in row.items()) + '}'


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n')


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline='')
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator='\n')
    w.writeheader()
    for row in rows:
        w.writerow({k: iso(v) if isinstance(v, datetime) else v for k, v in row.items()})
    path.write_text(buf.getvalue())


def auth_record(world: World, a: dict, file_slot: datetime, i: int) -> str:
    """One authorization as the processor writes it, with the planted problems of its file."""
    row = {k: v for k, v in a.items() if k != 'ring'}
    if file_slot == BAD_BATCH:
        row['amount'] = int(row['amount'] * 100)  # this one file is in cents
    if file_slot == COMMA_FILE and i < COMMA_ROWS:
        row['amount'] = f"{row['amount']}".replace('.', ',')  # a partner terminal: "12,50", a string
    if file_slot.date() >= WALLET_FROM:
        r = rng(world.seed, 'wallet', a['auth_id'])
        row['wallet_type'] = r.choice(['apple_pay', 'google_pay', None]) if a['entry_mode'] != 'chip' else None
    return jline(row)


def write(world: World, out: Path, first: date, last: date, only: set[str]) -> None:
    want = lambda s: not only or s in only
    if want('reference'):
        write_csv(out / 'reference' / 'merchants.csv', world.merchants())
        write_csv(out / 'reference' / 'mcc.csv', [{'mcc': m, 'description': d} for m, d in MCC])
        write_csv(out / 'reference' / 'branches.csv', [{'branch_id': b, 'name': n, 'region': r} for b, n, r in BRANCHES])
    for d in days(first, last):
        if want('card_auths'):
            for t, auths in world.card_files(d).items():
                write_lines(out / 'card_auths' / str(d) / f'auths-{t:%H%M}.json', [auth_record(world, a, t, i) for i, a in enumerate(auths)])
        if want('core_cdc'):
            for name, changes in world.cdc_files(d).items():
                write_lines(out / 'core_cdc' / str(d) / name, [jline({'op': ch['op'], 'seq': ch['seq'], 'ts': ch['ts'], 'table': ch['table'],
                                                                      'key': ch['key'], 'after': ch['after']}) for ch in changes])
        if want('postings'):
            rows = world.postings_on(d)
            if rows:
                write_csv(out / 'postings' / f'postings-{d}.csv', rows)
        if want('app_events'):
            hours: dict[int, list[str]] = {}
            for e in world.app_events_on(d):
                hours.setdefault(e['ts'].hour, []).append(jline(e))
            for h, lines in sorted(hours.items()):
                write_lines(out / 'app_events' / str(d) / f'events-{h:02d}.json', lines)
        if want('fx_rates'):
            write_csv(out / 'fx_rates' / f'fx-{d}.csv', world.fx_rates(d))
    if want('settlements'):  # clearing runs past the last authorization day
        end = SETTLE_LAST if last == LAST else last
        for d in days(first, end):
            rows = world.settlements_on(d)
            if rows:
                write_csv(out / 'settlements' / f'settlements-{d}.csv', rows)
    if want('chargebacks') and first <= date(2026, 10, 1) <= last + timedelta(days=1):
        write_csv(out / 'chargebacks' / 'chargebacks-2026-09.csv', world.chargebacks())
    if want('privacy') and first <= date(2026, 10, 25) <= last:
        write_csv(out / 'privacy' / 'erasure-requests-2026-10.csv', world.erasure_requests())


def stats(out: Path) -> int:
    """What landed, per source: files, records (CSV rows or JSON lines) and the days covered."""
    if not out.is_dir():
        print(f'✗ {out} does not exist: write the landing zone first')
        return 1
    print(f'{"source":<13}{"files":>7}{"records":>10}  {"first day":<11} last day')
    for source in SOURCES:
        files = sorted(p for p in (out / source).rglob('*') if p.is_file()) if (out / source).is_dir() else []
        if not files:
            continue
        records = sum(sum(1 for _ in p.open()) - (p.suffix == '.csv') for p in files)
        stamps = sorted(s for p in files for s in [p.parent.name if p.parent.name[:2] == '20' else p.stem[-10:]] if s[:2] == '20')
        span = f'{stamps[0]:<11} {stamps[-1]}' if stamps else ''
        print(f'{source:<13}{len(files):>7}{records:>10,}  {span}'.rstrip())
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog='python -m globalbank_sim', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', nargs='?', choices=['write', 'stats', 'verify'], default='write')
    p.add_argument('--sf', type=float, default=1.0, help='scale factor (1 = 5,000 customers, ~5,500 card authorizations a day)')
    p.add_argument('--seed', type=int, default=2026)
    p.add_argument('--out', type=Path, default=Path('landing'))
    p.add_argument('--from', dest='first', type=date.fromisoformat, default=FIRST)
    p.add_argument('--to', dest='last', type=date.fromisoformat, default=LAST)
    p.add_argument('--only', action='append', choices=SOURCES, default=[], help='only these sources (repeatable)')
    a = p.parse_args(argv)
    if a.command == 'stats':
        return stats(a.out)
    world = World(a.seed, a.sf)
    if a.command == 'verify':
        from .verify import verify
        return verify(world)
    write(world, a.out, a.first, a.last, set(a.only))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
