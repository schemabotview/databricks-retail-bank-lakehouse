"""Build spine/land/* from spine/start/06 (scratch builder, not part of the repo)."""
import json, shutil, sys
from pathlib import Path

ROOT = Path('/home/user/databricks-retail-bank-lakehouse/spine')
RESET = 'python "$SPINE_REPO/scripts/ws_reset.py"'
CAT = 'python -m globalbank.catalog'
land = lambda d: f'bash land.sh {d} > /dev/null'
INGEST = 'python -m globalbank.land > /dev/null'

CATALOG = '''"""Global Bank's catalog: a schema per medallion layer, and its volumes."""
from globalbank.session import get_spark

CATALOG = 'globalbank_dev'
LAYERS = ['landing', 'bronze', 'silver', 'gold']
VOLUMES = ['landing.card_auths', 'bronze.checkpoints']


def create(spark):
    spark.sql(f'CREATE CATALOG IF NOT EXISTS {CATALOG}')
    for layer in LAYERS:
        spark.sql(f'CREATE SCHEMA IF NOT EXISTS {CATALOG}.{layer}')
    for volume in VOLUMES:
        spark.sql(f'CREATE VOLUME IF NOT EXISTS {CATALOG}.{volume}')


if __name__ == '__main__':
    spark = get_spark()
    create(spark)
    schemas = spark.sql(f'SHOW SCHEMAS IN {CATALOG}').collect()
    print('schemas:', ', '.join(r.databaseName for r in schemas))
    for v in VOLUMES:
        print('volume: ', f'/Volumes/{CATALOG}/' + v.replace('.', '/'))
'''

REREAD = '''"""The naive way: read every file in the volume, on every run."""
from globalbank.session import get_spark

SOURCE = '/Volumes/globalbank_dev/landing/card_auths/'

spark = get_spark()
auths = spark.read.json(SOURCE + '*/')  # every day's folder
files = auths.select('_metadata.file_path').distinct().count()
print(f'read {auths.count():,} rows from {files} files')
'''

COLUMNS = '''"""Print a table's columns and their types, on one line."""
import sys

from globalbank.session import get_spark

table = sys.argv[1]
spark = get_spark()
print('  '.join(f'{n} {t}' for n, t in spark.table(table).dtypes))
'''

HEAD = '''"""Land card authorizations in bronze with Auto Loader: every file once."""
from globalbank.session import get_spark

SOURCE = '/Volumes/globalbank_dev/landing/card_auths/'
CHECKPOINT = '/Volumes/globalbank_dev/bronze/checkpoints/card_auths'
TABLE = 'globalbank_dev.bronze.card_auths'
'''

def land_py(hints=False, evolve=False, meta=False):
    third = (['from pyspark.errors import StreamingQueryException'] if evolve else []) + \
            (['from pyspark.sql import functions as F'] if meta else [])
    block = ('import re\n\n' if evolve else '') + ('\n'.join(third) + '\n\n' if third else '')
    head = HEAD.replace('from globalbank.session import get_spark\n', block + 'from globalbank.session import get_spark\n')
    if hints:
        head += "HINTS = 'amount DECIMAL(18,2), auth_ts TIMESTAMP'\n"
    read = ["    auths = (spark.readStream.format('cloudFiles')",
            "             .option('cloudFiles.format', 'json')",
            "             .option('cloudFiles.schemaLocation', CHECKPOINT)"]
    if hints:
        read.append("             .option('cloudFiles.schemaHints', HINTS)")
    if meta:
        read += ["             .load(SOURCE)",
                 "             .withColumn('source_file', F.col('_metadata.file_path'))",
                 "             .withColumn('landed_at',",
                 "                         F.col('_metadata.file_modification_time')))"]
    else:
        read.append("             .load(SOURCE))")
    write = ["    query = (auths.writeStream",
             "             .option('checkpointLocation', CHECKPOINT)"]
    if evolve:
        write.append("             .option('mergeSchema', 'true')")
    write += ["             .trigger(availableNow=True)",
              "             .toTable(TABLE))",
              "    query.awaitTermination()"]
    body = '\n\ndef ingest(spark):\n' + '\n'.join(read + write) + '\n'
    main = '''

if __name__ == '__main__':
    spark = get_spark()
    exists = spark.catalog.tableExists(TABLE)
    before = spark.table(TABLE).count() if exists else 0
'''
    if evolve:
        main += '''    try:
        ingest(spark)
    except StreamingQueryException as e:
        reason = re.search(r'\\[(UNKNOWN_FIELD_EXCEPTION[\\w.]*)\\]', str(e))
        found = re.search(r'Rescued record schema: (.*?) SQLSTATE', str(e))
        print('stream stopped:', reason.group(1) if reason else 'failed')
        print('new column:', found.group(1) if found else '?')
        raise SystemExit(1)
'''
    else:
        main += '    ingest(spark)\n'
    main += '''    after = spark.table(TABLE).count()
    print(f'{TABLE}: {before:,} + {after - before:,} = {after:,} rows')
'''
    return head + body + main

RESCUED = '''"""Rows whose fields did not fit the schema: kept, in _rescued_data."""
from pyspark.sql import functions as F

from globalbank.session import get_spark

TABLE = 'globalbank_dev.bronze.card_auths'

spark = get_spark()
(spark.table(TABLE)
    .where(F.col('_rescued_data').isNotNull())
    .select('auth_id', 'amount',
            F.get_json_object('_rescued_data', '$.amount').alias('rescued'))
    .orderBy('auth_id')
    .show())
'''

SOURCES = '''"""Where each row came from: its file, and when that file landed."""
from pyspark.sql import functions as F

from globalbank.session import get_spark

TABLE = 'globalbank_dev.bronze.card_auths'

spark = get_spark()
(spark.table(TABLE)
    .groupBy(F.element_at(F.split('source_file', '/'), -1).alias('file'),
             'landed_at')
    .count()
    .orderBy(F.desc('count'), 'file')
    .show(3, truncate=False))
'''

RECONCILE = '''"""Reconcile bronze with the volume: every file, every line, counted."""
from pyspark.sql import functions as F

from globalbank.session import get_spark

SOURCE = '/Volumes/globalbank_dev/landing/card_auths/'
TABLE = 'globalbank_dev.bronze.card_auths'

spark = get_spark()
lines = spark.read.text(SOURCE + '*/')
bronze = spark.table(TABLE)
rows, ids = bronze.count(), bronze.select('auth_id').distinct().count()
files = lines.select('_metadata.file_path').distinct().count()
counts = {
    'files in the volume': files,
    'files in bronze': bronze.select('source_file').distinct().count(),
    'lines in the files': lines.count(),
    'rows in bronze': rows,
    'distinct auth_id': ids,
    'sent twice': rows - ids,
    'rescued': bronze.where(F.col('_rescued_data').isNotNull()).count(),
}
for name, n in counts.items():
    print(f'{name:<20}{n:>8,}')
'''


def step(name, parent, changes, files, session, setup, remove=(), extra=None):
    d = ROOT / 'land' / name
    old = (d / 'session.txt').read_text() if (d / 'session.txt').exists() else ''
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(ROOT / parent / 'project', d / 'project', ignore=shutil.ignore_patterns('__pycache__', '.venv', 'landing'))
    for p in remove:
        (d / 'project' / p).unlink()
    for p, text in files.items():
        (d / 'project' / p).write_text(text)
    cfg = {'from': parent, 'workspace': True, 'venv': True, 'changes': changes, 'setup': setup}
    if extra:
        cfg.update(extra)
    (d / 'step.json').write_text(json.dumps(cfg, indent=1) + '\n')
    cmds = '\n'.join('$ ' + c for c in session) + '\n'
    kept = [l for l in old.splitlines() if l.startswith('$ ')] == [l for l in cmds.splitlines()]
    (d / 'session.txt').write_text(old if kept and old.strip() != cmds.strip() else cmds)


C = 'python -m globalbank.columns globalbank_dev.bronze.card_auths'
step('01-reread', 'start/06-first-table', ['globalbank/reread.py'], {'globalbank/reread.py': REREAD},
     ['python -m globalbank.reread', 'bash land.sh 2026-10-02 | wc -l', 'python -m globalbank.reread',
      'bash land.sh 2026-10-03 | wc -l', 'python -m globalbank.reread'],
     [RESET, CAT, land('2026-10-01')])
step('02-auto-loader', 'land/01-reread', ['globalbank/land.py', 'globalbank/columns.py', 'globalbank/catalog.py', 'globalbank/first_table.py'],
     {'globalbank/land.py': land_py(), 'globalbank/columns.py': COLUMNS, 'globalbank/catalog.py': CATALOG},
     ['python -m globalbank.land', 'bash land.sh 2026-10-03 | wc -l', 'python -m globalbank.land', C],
     [RESET, CAT, land('2026-10-01'), land('2026-10-02')], remove=['globalbank/first_table.py'])
step('03-checkpoint', 'land/02-auto-loader', ['globalbank/land.py'], {'globalbank/land.py': land_py()},
     ['python -m globalbank.land', 'databricks fs ls dbfs:/Volumes/globalbank_dev/bronze/checkpoints/card_auths',
      'databricks fs rm -r dbfs:/Volumes/globalbank_dev/bronze/checkpoints/card_auths', 'python -m globalbank.land'],
     [RESET, CAT, land('2026-10-01'), land('2026-10-02'), INGEST])
# 3.3 changes no code: a lab with 3.2's project.
d = ROOT / 'land' / '03-checkpoint'
if True:
  cfg = json.loads((d / 'step.json').read_text()); cfg.pop('from'); cfg.pop('changes'); cfg['lab'] = True
  (d / 'step.json').write_text(json.dumps(cfg, indent=1) + '\n')
step('04-schema-hints', 'land/02-auto-loader', ['globalbank/land.py'], {'globalbank/land.py': land_py(hints=True)},
     ['python -m globalbank.land', C], [RESET, CAT, land('2026-10-01')])
step('05-schema-evolution', 'land/04-schema-hints', ['globalbank/land.py'], {'globalbank/land.py': land_py(hints=True, evolve=True)},
     ['bash land.sh 2026-10-15 | wc -l', 'python -m globalbank.land', 'python -m globalbank.land', C],
     [RESET, CAT, land('2026-10-01'), INGEST])
step('06-rescued-data', 'land/05-schema-evolution', ['globalbank/rescued.py'], {'globalbank/rescued.py': RESCUED},
     ['bash land.sh 2026-10-20 | wc -l', 'python -m globalbank.land', 'python -m globalbank.rescued'],
     [RESET, CAT, land('2026-10-15'), 'python -m globalbank.land > /dev/null || true', INGEST])
step('07-file-metadata', 'land/06-rescued-data', ['globalbank/land.py', 'globalbank/sources.py'],
     {'globalbank/land.py': land_py(hints=True, evolve=True, meta=True), 'globalbank/sources.py': SOURCES},
     ['python -m globalbank.land', 'python -m globalbank.sources'],
     [RESET, CAT, land('2026-10-01')], extra={'volatile': ['ts']})
step('08-reconcile', 'land/07-file-metadata', ['globalbank/reconcile.py'], {'globalbank/reconcile.py': RECONCILE},
     ['python -m globalbank.reconcile'],
     [RESET, CAT, land('2026-10-01'), land('2026-10-02'), land('2026-10-03'), INGEST])
print('built')
