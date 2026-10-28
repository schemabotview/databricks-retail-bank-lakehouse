"""Build spine/operate/* from spine/ship/07 (scratch builder, not part of the repo).

12.1 reads this workspace's own bill (system.billing.usage, in DBUs: never prices) for the
course's replays so far. 12.2 and 12.3 use Course 3's Auto Loader script, one day per run, so the
table really is many small files. 12.5 and 12.6 are concept scenes with no step.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c5 import CAT, RESET, step  # noqa: E402

PARENT = 'ship/07-ci'
P = 'operate'

COST = '''"""This week's cost in DBUs by product, from the bill itself."""
from globalbank.session import get_spark

spark = get_spark()
rows = spark.sql("""
    SELECT billing_origin_product AS product, sku_name,
           round(sum(usage_quantity), 2) AS dbus
    FROM system.billing.usage
    WHERE usage_date >= current_date() - INTERVAL 7 DAYS
    GROUP BY ALL ORDER BY dbus DESC""").collect()
print(f'{sum(r.dbus for r in rows):.2f} DBUs in 7 days, by product:')
for r in rows[:8]:
    print(f'  {r.product:<20}{r.sku_name[:38]:<40}{r.dbus:>8.2f}')
'''

FILES = '''"""A table's files: how many, how big. Small files make every read slower."""
import sys

from globalbank.session import get_spark

table = sys.argv[1]
spark = get_spark()
d = spark.sql(f'DESCRIBE DETAIL {table}').first()
print(f'{table}: {d.numFiles} files, {d.sizeInBytes / 1e6:.1f} MB,'
      f' {d.sizeInBytes / max(d.numFiles, 1) / 1e3:.0f} KB a file')
'''

OPTIMIZE = '''"""Compact a table's small files into fewer, bigger ones."""
import sys

from globalbank.session import get_spark

table = sys.argv[1]
m = get_spark().sql(f'OPTIMIZE {table}').first().metrics
print(f'OPTIMIZE {table}: {m.numFilesRemoved} files removed,'
      f' {m.numFilesAdded} added')
'''

CLUSTER = '''"""Liquid clustering: the same query on the same rows, laid out two ways."""
import time

from databricks.sdk import WorkspaceClient

from globalbank.session import get_spark
from globalbank.warehouse import run

BRONZE = 'globalbank_dev.bronze.card_auths'
QUERY = """SELECT count(*), sum(amount) FROM {} WHERE merchant_id = 'M0001'
           AND to_date(auth_ts) = '2026-10-03'"""
spark = get_spark()
for name, layout in (('by_arrival', ''), ('clustered',
                                          'CLUSTER BY (merchant_id, auth_ts)')):
    spark.sql(f"""CREATE OR REPLACE TABLE globalbank_dev.silver.auths_{name}
                  {layout} AS SELECT * FROM {BRONZE}""")
    spark.sql(f'OPTIMIZE globalbank_dev.silver.auths_{name}')
w = WorkspaceClient()
for name in ('by_arrival', 'clustered'):
    run(w, QUERY.format(f'globalbank_dev.silver.auths_{name}'))
time.sleep(150)  # the query history arrives a few minutes later
_, rows = run(w, """
    SELECT regexp_extract(statement_text, 'auths_(\\\\w+)', 1) AS t,
           read_files, pruned_files
    FROM system.query.history
    WHERE statement_text LIKE '%M0001%auths_%'
      AND start_time > current_timestamp() - INTERVAL 15 MINUTES
    ORDER BY start_time DESC LIMIT 2""")
for t, read, pruned in sorted(rows):
    print(f'silver.auths_{t:<11} files read {read:>3}, skipped {pruned:>3}')
'''

PREDICTIVE = '''"""Predictive optimization: is it on here, and what has it run on our tables?"""
from globalbank.session import get_spark

spark = get_spark()
info = spark.sql('DESCRIBE SCHEMA EXTENDED globalbank_dev.silver').collect()
for r in info:
    if 'Predictive' in r[0]:
        print(f'{r[0]}: {r[1]}')
ops = spark.sql("""
    SELECT operation_type, count(*) AS n
    FROM system.storage.predictive_optimization_operations_history
    WHERE catalog_name = 'globalbank_dev' GROUP BY ALL""").collect()
print(f'operations on globalbank_dev so far: {len(ops)} kinds')
for o in ops:
    print(f'  {o.operation_type:<12}{o.n}')
history = spark.sql('DESCRIBE HISTORY globalbank_dev.silver.auths_clustered')
print('silver.auths_clustered, by operation:',
      ', '.join(f'{r.operation} {r.n}' for r in history.groupBy('operation')
                .count().withColumnRenamed('count', 'n').collect()))
'''

q = lambda c: c + ' > /dev/null'
DAYS = [f'2026-10-0{d}' for d in range(1, 8)]
SMALL = [RESET, CAT] + [x for d in DAYS for x in (f'bash land.sh {d} > /dev/null', q('python -m globalbank.land'))]
T = 'globalbank_dev.bronze.card_auths'
GO = {'continues': True}  # from the workspace as the step before left it

if __name__ == '__main__':
    step(P, '01-cost', PARENT, ['globalbank/cost.py'], {'globalbank/cost.py': COST},
         ['python -m globalbank.cost'], [RESET], extra={'volatile': ['digits']})
    step(P, '02-small-files', f'{P}/01-cost', ['globalbank/files.py', 'globalbank/optimize.py'],
         {'globalbank/files.py': FILES, 'globalbank/optimize.py': OPTIMIZE},
         [f'python -m globalbank.files {T}', f'python -m globalbank.optimize {T}', f'python -m globalbank.files {T}'], SMALL)
    step(P, '03-liquid-clustering', f'{P}/02-small-files', ['globalbank/cluster.py'], {'globalbank/cluster.py': CLUSTER},
         ['python -m globalbank.cluster'], [], extra=GO)
    step(P, '04-predictive', f'{P}/03-liquid-clustering', ['globalbank/predictive.py'], {'globalbank/predictive.py': PREDICTIVE},
         ['python -m globalbank.predictive'], [], extra=GO)
    print('built')
