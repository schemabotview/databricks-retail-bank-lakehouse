"""Build spine/ledger/* from spine/land/08 (scratch builder, not part of the repo)."""
import json, shutil
from pathlib import Path

ROOT = Path('/home/user/databricks-retail-bank-lakehouse/spine')
RESET = 'python "$SPINE_REPO/scripts/ws_reset.py"'
CAT = 'python -m globalbank.catalog'
land = lambda d, src='': f'bash land.sh {d} {src}'.rstrip() + ' > /dev/null'
INGEST = 'python -m globalbank.land > /dev/null'
post = lambda d: f'python -m globalbank.ledger post {d} > /dev/null'
DAYS = ['2026-10-10', '2026-10-11', '2026-10-12', '2026-10-13']
BASE_SETUP = [RESET, CAT] + [land(d) for d in DAYS + ['2026-10-14']] + [INGEST]
POSTED = BASE_SETUP + [post(d) for d in DAYS]

LEDGER1 = """\"\"\"Silver card_transactions: bronze's authorizations, one row per auth_id.\"\"\"
import sys

from globalbank.session import get_spark

BRONZE = 'globalbank_dev.bronze.card_auths'
SILVER = 'globalbank_dev.silver.card_transactions'


def create(spark):
    spark.sql(f\"\"\"CREATE TABLE IF NOT EXISTS {SILVER} (
        auth_id STRING NOT NULL, card_id STRING, merchant_id STRING,
        mcc STRING, amount DECIMAL(18,2), currency STRING,
        auth_ts TIMESTAMP, status STRING, source_file STRING,
        settled_eur DECIMAL(18,2), cleared_date DATE)\"\"\")
#CONSTRAINT#

def post(spark, day):
    \"\"\"Merge one day of authorizations: a resent one is inserted once.\"\"\"
    spark.sql(f\"\"\"MERGE INTO {SILVER} t
        USING (SELECT * FROM {BRONZE} WHERE to_date(auth_ts) = '{day}'
               QUALIFY row_number() OVER (PARTITION BY auth_id
                                          ORDER BY landed_at) = 1) s
        ON t.auth_id = s.auth_id
        WHEN NOT MATCHED THEN INSERT (auth_id, card_id, merchant_id, mcc,
            amount, currency, auth_ts, status, source_file)
        VALUES (s.auth_id, s.card_id, s.merchant_id, s.mcc, s.amount,
            s.currency, s.auth_ts, s.status, s.source_file)\"\"\")
#SETTLE#

if __name__ == '__main__':
    spark = get_spark()
    create(spark)
    verb, day = sys.argv[1], sys.argv[2]
#RUN#
    print(f'{SILVER}: {spark.table(SILVER).count():,} rows')
"""
RUN1 = "    {'post': post}[verb](spark, day)"
RUN4 = """    try:
        {'post': post}[verb](spark, day)
    except Exception as e:
        reason = re.search(r'\\[(DELTA_\\w+)\\]', str(e))
        print('refused:', reason.group(1) if reason else type(e).__name__)
        print(str(e).split('\\n')[1].strip()[:72])
        raise SystemExit(1)"""
CONSTRAINT = """    constraints = spark.sql(f'SHOW TBLPROPERTIES {SILVER}').collect()
    if not any(r.key == 'delta.constraints.amount_in_range'
               for r in constraints):
        # An illustrative per-authorization limit, not a real card rule.
        spark.sql(f\"\"\"ALTER TABLE {SILVER} ADD CONSTRAINT amount_in_range
                       CHECK (amount > 0 AND amount <= 1000)\"\"\")
"""
SETTLE = """

def settle(spark, day):
    \"\"\"Apply one day's clearing file: settled, or reversed.\"\"\"
    spark.sql(f\"\"\"MERGE INTO {SILVER} t
        USING (SELECT * FROM {CLEARING} WHERE cleared_date = '{day}') s
        ON t.auth_id = s.auth_id
        WHEN MATCHED THEN UPDATE SET
            status = IF(s.kind = 'REVERSAL', 'REVERSED', 'SETTLED'),
            settled_eur = s.amount_eur, cleared_date = s.cleared_date\"\"\")
"""
CDF = """    spark.sql(f\"\"\"ALTER TABLE {SILVER}
                   SET TBLPROPERTIES (delta.enableChangeDataFeed = true)\"\"\")
"""
def ledger(constraint=False, settle=False, cdf=False):
    t = LEDGER1
    if constraint:
        t = t.replace('import sys\n', 'import re\nimport sys\n').replace('#RUN#', RUN4.replace("{'post': post}", "{'post': post, 'settle': settle}" if settle else "{'post': post}"))
    else:
        t = t.replace('#RUN#', RUN1)
    t = t.replace('#CONSTRAINT#\n', (CONSTRAINT if constraint else '') + (CDF if cdf else ''))
    t = t.replace('#SETTLE#\n', SETTLE if settle else '')
    if settle:
        t = t.replace("SILVER = 'globalbank_dev.silver.card_transactions'\n", "SILVER = 'globalbank_dev.silver.card_transactions'\nCLEARING = 'globalbank_dev.bronze.settlements'\n")
    import re as _re
    return _re.sub(r'\n+(def |if __name__)', r'\n\n\n\1', t)

DAILY = '''"""Approved card spend per day, in silver; optionally as of a version."""
import sys

from globalbank.session import get_spark

SILVER = 'globalbank_dev.silver.card_transactions'

spark = get_spark()
version = f' VERSION AS OF {sys.argv[1]}' if len(sys.argv) > 1 else ''
spark.sql(f"""SELECT to_date(auth_ts) AS day, count(*) AS auths,
                     sum(amount) AS spend
              FROM {SILVER}{version}
              WHERE status = 'APPROVED' AND currency = 'EUR'
              GROUP BY day ORDER BY day""").show()
'''

HISTORY = '''"""A table's history: one row per version, with what wrote it."""
import sys

from pyspark.sql import functions as F

from globalbank.session import get_spark

spark = get_spark()
(spark.sql(f'DESCRIBE HISTORY {sys.argv[1]}')
    .select('version', 'operation',
            F.coalesce(F.col('operationMetrics.numTargetRowsInserted'),
                       F.col('operationMetrics.numOutputRows'),
                       F.lit('')).alias('rows'))
    .orderBy('version')
    .show(truncate=False))
'''

RESTORE = '''"""Put a table back to an earlier version. The restore is a version too."""
import sys

from globalbank.session import get_spark

table, version = sys.argv[1], sys.argv[2]
spark = get_spark()
result = spark.sql(f'RESTORE TABLE {table} TO VERSION AS OF {version}')
print(result.select('restored_files_size', 'num_restored_files').first())
'''


def step(name, parent, changes, files, session, setup, remove=(), extra=None, lab=False):
    d = ROOT / 'ledger' / name
    old = (d / 'session.txt').read_text() if (d / 'session.txt').exists() else ''
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(ROOT / parent / 'project', d / 'project', ignore=shutil.ignore_patterns('__pycache__', '.venv', 'landing'))
    for p in remove:
        (d / 'project' / p).unlink()
    for p, text in files.items():
        (d / 'project' / p).parent.mkdir(parents=True, exist_ok=True)
        (d / 'project' / p).write_text(text)
    cfg = {'lab': True} if lab else {'from': parent, 'changes': changes}
    cfg.update({'workspace': True, 'venv': True, 'setup': setup})
    if extra:
        cfg.update(extra)
    (d / 'step.json').write_text(json.dumps(cfg, indent=1) + '\n')
    cmds = '\n'.join('$ ' + c for c in session) + '\n'
    kept = [l for l in old.splitlines() if l.startswith('$ ')] == [l for l in cmds.splitlines()]
    (d / 'session.txt').write_text(old if kept and old.strip() != cmds.strip() else cmds)


SILVER = 'globalbank_dev.silver.card_transactions'
step('01-bad-batch', 'land/08-reconcile', ['globalbank/ledger.py', 'globalbank/daily.py'],
     {'globalbank/ledger.py': ledger(), 'globalbank/daily.py': DAILY},
     ['python -m globalbank.ledger post 2026-10-14', 'python -m globalbank.daily'], POSTED)
step('02-time-travel', 'ledger/01-bad-batch', ['globalbank/history.py'], {'globalbank/history.py': HISTORY},
     [f'python -m globalbank.history {SILVER}', 'python -m globalbank.daily 4'], POSTED + [post('2026-10-14')])
step('03-restore', 'ledger/02-time-travel', ['globalbank/restore.py'], {'globalbank/restore.py': RESTORE},
     [f'python -m globalbank.restore {SILVER} 4', f'python -m globalbank.history {SILVER}', 'python -m globalbank.daily'],
     POSTED + [post('2026-10-14')])

LAND_SH = """#!/usr/bin/env bash
# Land one day of a source: generate its files for that day, then copy
# them into the source's landing volume, as they are.
set -euo pipefail

day=$1
source=${2:-card_auths}
volume=dbfs:/Volumes/globalbank_dev/landing/$source

python -m globalbank_sim --out landing --from "$day" --to "$day" \\
  --only "$source"
if [ -d "landing/$source/$day" ]; then  # a folder per day
  databricks fs cp -r "landing/$source/$day" "$volume/$day"
else                                     # a file per day
  databricks fs cp "landing/$source/$source-$day.csv" "$volume/"
fi
"""

LAND_PY = """\"\"\"Land a source in bronze with Auto Loader: every file once.\"\"\"
import re
import sys

from pyspark.errors import StreamingQueryException
from pyspark.sql import functions as F

from globalbank.session import get_spark

SOURCES = {
    'card_auths': ('json', 'amount DECIMAL(18,2), auth_ts TIMESTAMP'),
    'settlements': ('csv', 'amount DECIMAL(18,2), amount_eur DECIMAL(18,2),'
                           ' cleared_date DATE'),
}


def ingest(spark, source):
    fmt, hints = SOURCES[source]
    checkpoint = f'/Volumes/globalbank_dev/bronze/checkpoints/{source}'
    rows = (spark.readStream.format('cloudFiles')
            .option('cloudFiles.format', fmt)
            .option('cloudFiles.schemaLocation', checkpoint)
            .option('cloudFiles.schemaHints', hints)
            .option('header', 'true')  # CSV: line 1 names the columns
            .load(f'/Volumes/globalbank_dev/landing/{source}/')
            .withColumn('source_file', F.col('_metadata.file_path'))
            .withColumn('landed_at',
                        F.col('_metadata.file_modification_time')))
    query = (rows.writeStream
             .option('checkpointLocation', checkpoint)
             .option('mergeSchema', 'true')
             .trigger(availableNow=True)
             .toTable(f'globalbank_dev.bronze.{source}'))
    query.awaitTermination()


if __name__ == '__main__':
    source = sys.argv[1] if len(sys.argv) > 1 else 'card_auths'
    table = f'globalbank_dev.bronze.{source}'
    spark = get_spark()
    exists = spark.catalog.tableExists(table)
    before = spark.table(table).count() if exists else 0
    try:
        ingest(spark, source)
    except StreamingQueryException as e:
        reason = re.search(r'\\[(UNKNOWN_FIELD_EXCEPTION[\\w.]*)\\]', str(e))
        found = re.search(r'Rescued record schema: (.*?) SQLSTATE', str(e))
        print('stream stopped:', reason.group(1) if reason else 'failed')
        print('new column:', found.group(1) if found else '?')
        raise SystemExit(1)
    after = spark.table(table).count()
    print(f'{table}: {before:,} + {after - before:,} = {after:,} rows')
"""

WRITERS = """\"\"\"Two writers, one table: post two days at the same moment.\"\"\"
import sys
from concurrent.futures import ThreadPoolExecutor

from globalbank.ledger import SILVER, create, post
from globalbank.session import get_spark

spark = get_spark()
create(spark)
with ThreadPoolExecutor(max_workers=2) as pool:
    done = pool.map(lambda day: post(spark, day), sys.argv[1:])
    list(done)  # raises here if either writer failed
for day in sys.argv[1:]:
    print(f'{day}: committed')
print(f'{SILVER}: {spark.table(SILVER).count():,} rows')
"""

STATUSES = open('statuses.tpl').read()

DV = """\"\"\"What the last MERGE did to the files: rewrite, or mark.\"\"\"
from globalbank.session import get_spark

SILVER = 'globalbank_dev.silver.card_transactions'

spark = get_spark()
last = spark.sql(f'DESCRIBE HISTORY {SILVER} LIMIT 1').first()
m = last.operationMetrics
print(f'version {last.version}: {last.operation}')
for key in ['numTargetRowsUpdated', 'numTargetFilesAdded',
            'numTargetFilesRemoved', 'numTargetDeletionVectorsAdded']:
    print(f'  {key:<31}{m.get(key, "-"):>7}')
features = spark.sql(f'DESCRIBE DETAIL {SILVER}').first().tableFeatures
print('table features:', ', '.join(sorted(features)))
"""

CHANGES = open('changes.tpl').read()

CATALOG6 = open(ROOT / 'land' / '08-reconcile' / 'project' / 'globalbank' / 'catalog.py').read().replace(
    "VOLUMES = ['landing.card_auths', 'bronze.checkpoints']",
    "VOLUMES = ['landing.card_auths', 'landing.settlements', 'bronze.checkpoints']")

POSTED6 = POSTED + [post('2026-10-15'), post('2026-10-16')]
INGEST2 = 'python -m globalbank.land > /dev/null || python -m globalbank.land > /dev/null'
LANDED_ALL = [RESET, CAT] + [land(d) for d in DAYS + ['2026-10-14', '2026-10-15', '2026-10-16']] + [INGEST2]
POSTED_ALL = LANDED_ALL + [post(d) for d in DAYS + ['2026-10-15', '2026-10-16']]
CLEAR = [land(d, 'settlements') for d in ['2026-10-11', '2026-10-12', '2026-10-13']] + ['python -m globalbank.land settlements > /dev/null']
settle = lambda d: f'python -m globalbank.ledger settle {d} > /dev/null'

step('04-constraints', 'ledger/03-restore', ['globalbank/ledger.py'], {'globalbank/ledger.py': ledger(constraint=True)},
     ['python -m globalbank.ledger post 2026-10-14', f'python -m globalbank.history {SILVER}'],
     POSTED + [post('2026-10-14'), f'python -m globalbank.restore {SILVER} 4 > /dev/null'])
step('05-two-writers', 'ledger/04-constraints', ['globalbank/writers.py'], {'globalbank/writers.py': WRITERS},
     ['python -m globalbank.writers 2026-10-15 2026-10-16', f'python -m globalbank.history {SILVER}'],
     LANDED_ALL + [post(d) for d in DAYS])
step('06-settle', 'ledger/05-two-writers', ['globalbank/ledger.py', 'globalbank/land.py', 'globalbank/catalog.py', 'land.sh', 'globalbank/statuses.py'],
     {'globalbank/ledger.py': ledger(constraint=True, settle=True), 'globalbank/land.py': LAND_PY, 'globalbank/catalog.py': CATALOG6,
      'land.sh': LAND_SH, 'globalbank/statuses.py': STATUSES},
     ['bash land.sh 2026-10-11 settlements | wc -l', 'python -m globalbank.land settlements',
      'python -m globalbank.ledger settle 2026-10-11', 'python -m globalbank.statuses'],
     POSTED_ALL)
step('07-deletion-vectors', 'ledger/06-settle', ['globalbank/dv.py'], {'globalbank/dv.py': DV},
     ['python -m globalbank.ledger settle 2026-10-12', 'python -m globalbank.dv'],
     POSTED_ALL + CLEAR + [settle('2026-10-11')])
step('08-change-feed', 'ledger/07-deletion-vectors', ['globalbank/ledger.py', 'globalbank/changes.py'],
     {'globalbank/ledger.py': ledger(constraint=True, settle=True, cdf=True), 'globalbank/changes.py': CHANGES},
     ['python -m globalbank.ledger settle 2026-10-13', 'python -m globalbank.changes'],
     POSTED_ALL + CLEAR + [settle('2026-10-11'), settle('2026-10-12')])
print('built')
