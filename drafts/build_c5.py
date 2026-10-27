"""Build spine/customers/* from spine/ledger/08 (scratch builder, not part of the repo).

Run from anywhere: python3.12 drafts/build_c5.py. Each step is its parent's project plus the files
given here; step() keeps an existing session.txt when its commands did not change.
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'spine'
RESET = 'python "$SPINE_REPO/scripts/ws_reset.py"'
CAT = 'python -m globalbank.catalog'


def step(course, name, parent, changes, files, session, setup, lab=False, extra=None):
    d = ROOT / course / name
    old = (d / 'session.txt').read_text() if (d / 'session.txt').exists() else ''
    shutil.rmtree(d / 'project', ignore_errors=True)
    shutil.copytree(ROOT / parent / 'project', d / 'project', ignore=shutil.ignore_patterns('__pycache__', '.venv', 'landing'))
    for p, text in files.items():
        if text is None:
            (d / 'project' / p).unlink()
            continue
        (d / 'project' / p).parent.mkdir(parents=True, exist_ok=True)
        (d / 'project' / p).write_text(text)
    cfg = {'lab': True} if lab else {'from': parent, 'changes': changes}
    cfg.update({'workspace': True, 'venv': True, 'setup': setup})
    cfg.update(extra or {})
    (d / 'step.json').write_text(json.dumps(cfg, indent=1) + '\n')
    cmds = '\n'.join('$ ' + c for c in session) + '\n'
    kept = [l for l in old.splitlines() if l.startswith('$ ')] == [l for l in cmds.splitlines()]
    (d / 'session.txt').write_text(old if kept and old.strip() else cmds)


def read(path):
    return (ROOT / path).read_text()


LAND_SH = """#!/usr/bin/env bash
# Land a source's files for a day, or a range of days: generate them as the
# source sends them, then copy them into its landing volume, as they are.
set -euo pipefail

first=$1
source=${2:-card_auths}
last=${3:-$first}
batch=landing/.batch  # only this run's files

rm -rf "$batch"
python -m globalbank_sim --out "$batch" --from "$first" --to "$last" \\
  --only "$source"
databricks fs cp -r "$batch/$source" \\
  "dbfs:/Volumes/globalbank_dev/landing/$source"
"""

PARENT = 'ledger/08-change-feed'
land_py = read(f'{PARENT}/project/globalbank/land.py').replace(
    """                           ' cleared_date DATE'),
}""", """                           ' cleared_date DATE'),
    'core_cdc': ('json', 'seq BIGINT, ts TIMESTAMP'),
}""")
assert 'core_cdc' in land_py
catalog_py = read(f'{PARENT}/project/globalbank/catalog.py').replace(
    "'landing.settlements', ", "'landing.settlements', 'landing.core_cdc',\n           ")
assert 'core_cdc' in catalog_py

RECORD = '''"""What the core system sends: change records, counted, and one taken apart."""
import sys

from globalbank.session import get_spark

BRONZE = 'globalbank_dev.bronze.core_cdc'

spark = get_spark()
counts = spark.sql(f"""SELECT `table`, op, count(*) AS n FROM {BRONZE}
                       GROUP BY ALL ORDER BY ALL""").collect()
print('   '.join(f'{r.table} {r.op} {r.n:,}' for r in counts))
change = spark.table(BRONZE).where(f'seq = {sys.argv[1]}').first()
print('one change, as received:')
print(f'  op {change.op}   seq {change.seq}   table {change.table}'
      f'   ts {change.ts}')
print(f'  key    {change.key}')
lines = ['']
for part in change.after.split(','):  # wrap between fields, not inside one
    if len(lines[-1]) + len(part) > 68:
        lines.append('')
    lines[-1] += part + ','
print('  after  ' + '\\n         '.join(lines).rstrip(','))
'''

CUSTOMERS = """    'customers': ('customer_id',
                  'customer_id STRING, first_name STRING, last_name STRING,'
                  ' national_id STRING, date_of_birth DATE, email STRING,'
                  ' address STRING, region STRING, branch_id STRING,'
                  ' segment STRING, kyc_status STRING, customer_since DATE'),
"""
ACCOUNTS = """    'accounts': ('account_id',
                 'account_id STRING, customer_id STRING, product STRING,'
                 ' iban STRING, opened DATE, status STRING,'
                 ' overdraft_limit DECIMAL(18,2),'
                 ' opening_balance DECIMAL(18,2)'),
"""


def cdc(guard=False, accounts=False):
    when = ' AND s.seq > t.seq' if guard else ''
    return f'''"""Silver customers and accounts from the core system's changes (SCD type 1)."""
import sys

from globalbank.session import get_spark

BRONZE = 'globalbank_dev.bronze.core_cdc'
TABLES = {{  # table: (key, columns)
{CUSTOMERS}{ACCOUNTS if accounts else ''}}}


def apply(spark, table, files):
    """Apply a batch of change files to silver: the latest change per key."""
    key, schema = TABLES[table]
    silver = f'globalbank_dev.silver.{{table}}'
    spark.sql(f'CREATE TABLE IF NOT EXISTS {{silver}} ({{schema}}, seq BIGINT)')
    cols = [c.split()[0] for c in schema.split(', ')]
    batch = spark.sql(f"""
        SELECT op, seq, get_json_object(key, '$.{{key}}') AS k,
               from_json(after, '{{schema}}') AS a
        FROM {{BRONZE}}
        WHERE `table` = '{{table}}' AND source_file RLIKE '{{files}}'
        QUALIFY row_number() OVER (PARTITION BY k ORDER BY seq DESC) = 1""")
    batch.createOrReplaceTempView('batch')
    spark.sql(f"""MERGE INTO {{silver}} t USING batch s ON t.{{key}} = s.k
        WHEN MATCHED{when} AND s.op = 'D' THEN DELETE
        WHEN MATCHED{when} THEN UPDATE SET
            {{', '.join(f't.{{c}} = s.a.{{c}}' for c in cols)}}, t.seq = s.seq
        WHEN NOT MATCHED AND s.op != 'D' THEN INSERT ({{', '.join(cols)}}, seq)
            VALUES ({{', '.join(f's.a.{{c}}' for c in cols)}}, s.seq)""")
    return batch.count()


if __name__ == '__main__':
    spark = get_spark()
    table, files = sys.argv[1], sys.argv[2]
    n = apply(spark, table, files)
    silver = f'globalbank_dev.silver.{{table}}'
    m = spark.sql(f'DESCRIBE HISTORY {{silver}} LIMIT 1').first().operationMetrics
    print(f'{{table}} <- {{files}}: {{n:,}} changes')
    print(f"  inserted {{m['numTargetRowsInserted']}},"
          f" updated {{m['numTargetRowsUpdated']}},"
          f" deleted {{m['numTargetRowsDeleted']}};"
          f" silver.{{table}}: {{spark.table(silver).count():,}} rows")
'''


CUSTOMER = '''"""One customer: every change the core system sent, and silver's row now."""
import sys

from globalbank.session import get_spark

customer = sys.argv[1]
spark = get_spark()
changes = spark.sql(f"""
    SELECT regexp_extract(source_file, 'core_cdc/(.*).json', 1) AS file,
           seq, op, after:address AS address
    FROM globalbank_dev.bronze.core_cdc
    WHERE key:customer_id = '{customer}'
    ORDER BY source_file, seq""").collect()
print(f'{customer}, in the order the changes arrived:')
for c in changes:
    print(f'  {c.file}  seq {c.seq:>5}  {c.op}  {c.address}')
row = spark.table('globalbank_dev.silver.customers') \\
    .where(f"customer_id = '{customer}'").first()
print(f'silver now: seq {row.seq}, {row.address}')
'''

CLOSED = '''"""Closed accounts: gone from silver, still in bronze's change records."""
from globalbank.session import get_spark

spark = get_spark()
closed = spark.sql("""
    SELECT b.key:account_id AS account_id, b.seq,
           regexp_extract(b.source_file, 'core_cdc/(.*)', 1) AS file,
           s.account_id IS NOT NULL AS in_silver
    FROM globalbank_dev.bronze.core_cdc b
    LEFT JOIN globalbank_dev.silver.accounts s
      ON s.account_id = b.key:account_id
    WHERE b.`table` = 'accounts' AND b.op = 'D'""")
print(f'{closed.count()} D records in bronze;'
      f' {closed.where("in_silver").count()} of their accounts in silver')
for c in closed.orderBy('seq').limit(3).collect():
    print(f"  {c.account_id}  seq {c.seq}  {c.file}"
          f"  in silver: {'yes' if c.in_silver else 'no'}")
'''

SCD2 = '''"""Silver customers_history: every version of each customer (SCD type 2)."""
import sys

from globalbank.cdc import BRONZE, TABLES
from globalbank.session import get_spark

HISTORY = 'globalbank_dev.silver.customers_history'


def build(spark):
    """Rebuild the history from bronze: each change holds until the next."""
    _, schema = TABLES['customers']
    spark.sql(f"""CREATE OR REPLACE TABLE {HISTORY} AS
        SELECT a.*, seq, ts AS valid_from,
               lead(ts) OVER (PARTITION BY a.customer_id
                              ORDER BY seq) AS valid_to,
               valid_to IS NULL AS is_current
        FROM (SELECT from_json(after, '{schema}') AS a, seq, ts
              FROM {BRONZE} WHERE `table` = 'customers')""")


if __name__ == '__main__':
    spark = get_spark()
    build(spark)
    history = spark.table(HISTORY)
    print(f'{HISTORY}: {history.count():,} versions of '
          f'{history.where("is_current").count():,} customers')
    (history.where(f"customer_id = '{sys.argv[1]}'")
        .select('seq', 'valid_from', 'valid_to', 'address', 'kyc_status')
        .orderBy('seq').show(truncate=False))
'''

PIT = '''"""A payment joined to its customer's KYC status then, and now."""
from globalbank.session import get_spark

spark = get_spark()
spark.sql("""
    SELECT a.auth_id, a.auth_ts, c.customer_id
    FROM globalbank_dev.bronze.card_auths a
    JOIN globalbank_dev.silver.accounts c
      ON a.card_id = 'K' || substr(c.account_id, 2, 6)
     AND c.product = 'current'""").createOrReplaceTempView('paid')
both = spark.sql("""
    SELECT p.auth_id, p.auth_ts, p.customer_id,
           h.kyc_status AS kyc_then, now.kyc_status AS kyc_now
    FROM paid p
    JOIN globalbank_dev.silver.customers now USING (customer_id)
    JOIN globalbank_dev.silver.customers_history h
      ON h.customer_id = p.customer_id
     AND p.auth_ts >= h.valid_from
     AND (p.auth_ts < h.valid_to OR h.valid_to IS NULL)""")
differ = both.where('kyc_then != kyc_now')
print(f'{both.count():,} payments;'
      f' {differ.count():,} with another KYC status then')
differ.orderBy('auth_ts').show(5, truncate=False)
'''

C = 'customers'
LANDED = [RESET, CAT, 'bash land.sh 2026-09-01 core_cdc 2026-10-09 > /dev/null']
INGESTED = LANDED + ['python -m globalbank.land core_cdc > /dev/null']
apply = lambda t, f: f"python -m globalbank.cdc {t} '{f}'"
SEPT, OCT8, OCT = '2026-09-', '2026-10-0[1-8]', '2026-10-0'
TO_OCT8 = INGESTED + [apply('customers', SEPT) + ' > /dev/null', apply('customers', OCT8) + ' > /dev/null']
OOO = [apply('customers', '2026-10-09/changes-1200'), apply('customers', '2026-10-09/changes-2359'),
       'python -m globalbank.customer C000001']

if __name__ == '__main__':
    step(C, '01-change-records', PARENT, ['land.sh', 'globalbank/land.py', 'globalbank/catalog.py', 'globalbank/record.py'],
         {'land.sh': LAND_SH, 'globalbank/land.py': land_py, 'globalbank/catalog.py': catalog_py, 'globalbank/record.py': RECORD},
         ['python -m globalbank.land core_cdc', 'python -m globalbank.record 12155'], LANDED)
    step(C, '02-current-state', f'{C}/01-change-records', ['globalbank/cdc.py'], {'globalbank/cdc.py': cdc()},
         [apply('customers', SEPT), apply('customers', OCT8)], INGESTED)
    step(C, '03-out-of-order', f'{C}/02-current-state', ['globalbank/customer.py'], {'globalbank/customer.py': CUSTOMER},
         OOO, TO_OCT8)
    step(C, '04-in-sequence', f'{C}/03-out-of-order', ['globalbank/cdc.py'], {'globalbank/cdc.py': cdc(guard=True)},
         OOO, TO_OCT8)
    step(C, '05-deletes', f'{C}/04-in-sequence', ['globalbank/cdc.py', 'globalbank/closed.py'],
         {'globalbank/cdc.py': cdc(guard=True, accounts=True), 'globalbank/closed.py': CLOSED},
         [apply('accounts', SEPT), apply('accounts', OCT), 'python -m globalbank.closed'], INGESTED)
    step(C, '06-history', f'{C}/05-deletes', ['globalbank/scd2.py'], {'globalbank/scd2.py': SCD2},
         ['python -m globalbank.scd2 C000001'], INGESTED)
    step(C, '07-point-in-time', f'{C}/06-history', ['globalbank/pit.py'], {'globalbank/pit.py': PIT},
         ['python -m globalbank.pit'],
         INGESTED + ['bash land.sh 2026-09-28 card_auths 2026-09-30 > /dev/null', 'python -m globalbank.land > /dev/null',
                     apply('customers', '2026-') + ' > /dev/null', apply('accounts', '2026-') + ' > /dev/null',
                     'python -m globalbank.scd2 C000001 > /dev/null'])
    print('built')
