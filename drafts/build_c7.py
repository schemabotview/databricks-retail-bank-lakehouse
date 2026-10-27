"""Build spine/pipeline/* from spine/protect/08 (scratch builder, not part of the repo).

The pipeline is `globalbank_pipeline`: Lakeflow Spark Declarative Pipelines (`from pyspark import
pipelines as dp`), serverless, one pipeline for the whole medallion (Free Edition: one per type).
globalbank/deploy.py uploads pipelines/*.py and creates or updates it (Course 11 replaces it with a
bundle); globalbank/run.py starts an update, waits, and prints what each dataset holds, read from
the tables and the event log. ws_reset.py deletes the pipeline before every step, so each step
starts from no pipeline at all.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c5 import CAT, RESET, read, step  # noqa: E402

PARENT = 'protect/08-erasure'
P = 'pipeline'

NIGHTLY = """#!/usr/bin/env bash
# The nightly run, by hand: one script after another, in the order typed.
set -euo pipefail

day=$1
bash land.sh "$day" > /dev/null
bash land.sh "$day" core_cdc > /dev/null
python -m globalbank.ledger post "$day"        # silver: card transactions
python -m globalbank.land                       # bronze: card authorizations
python -m globalbank.land core_cdc              # bronze: core changes
python -m globalbank.cdc customers "$day"       # silver: customers
"""

DEPLOY = '''"""Deploy globalbank_pipeline: upload pipelines/*.py, create or update it."""
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.pipelines import FileLibrary, PipelineLibrary
from databricks.sdk.service.workspace import ImportFormat

NAME = 'globalbank_pipeline'


def deploy(w):
    folder = f'/Workspace/Users/{w.current_user.me().user_name}/globalbank'
    w.workspace.mkdirs(f'{folder}/pipelines')
    sources = sorted(Path('pipelines').glob('*.py'))
    for source in sources:
        w.workspace.upload(f'{folder}/{source}', source.open('rb'),
                           format=ImportFormat.RAW, overwrite=True)
    settings = dict(
        name=NAME, serverless=True, catalog='globalbank_dev', schema='bronze',
        libraries=[PipelineLibrary(file=FileLibrary(path=f'{folder}/{s}'))
                   for s in sources])
    found = list(w.pipelines.list_pipelines(filter=f"name LIKE '{NAME}'"))
    if found:
        w.pipelines.update(found[0].pipeline_id, **settings)
        return found[0].pipeline_id, 'updated', sources
    return w.pipelines.create(**settings).pipeline_id, 'created', sources


if __name__ == '__main__':
    _, verb, sources = deploy(WorkspaceClient())
    print(f"{NAME}: {verb}, {len(sources)} source file(s):"
          f" {', '.join(s.name for s in sources)}")
'''

RUN = '''"""Run globalbank_pipeline once and wait: what each dataset holds after it."""
import sys
import time

from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark



def start(w, pipeline_id, **kwargs):
    for _ in range(12):  # a pipeline created a moment ago may not be found yet
        try:
            return w.pipelines.start_update(pipeline_id, **kwargs).update_id
        except Exception:
            time.sleep(10)
    raise SystemExit('the pipeline never became ready')


if __name__ == '__main__':
    w = WorkspaceClient()
    pipeline = next(w.pipelines.list_pipelines(filter=f"name LIKE '{NAME}'"))
    update = start(w, pipeline.pipeline_id,
                   full_refresh='--full-refresh' in sys.argv)
    while (state := w.pipelines.get_update(pipeline.pipeline_id, update)
           .update.state.value) not in ('COMPLETED', 'FAILED', 'CANCELED'):
        time.sleep(10)
    print(f'update {state}')
    if state != 'COMPLETED':
        errors = [e.message for e in w.pipelines.list_pipeline_events(
            pipeline.pipeline_id,
            filter=f"level='ERROR' AND update_id='{update}'")]
        raise SystemExit('\\n'.join(m[:78] for m in errors[-2:]))
    spark = get_spark()
    events = spark.sql(f"""SELECT * FROM event_log('{pipeline.pipeline_id}')
                           WHERE origin.update_id = '{update}'""")
    datasets = events.where("event_type = 'flow_definition'").selectExpr(
        'details:flow_definition.output_dataset AS name').distinct().collect()
    planned = events.where("event_type = 'planning_information'")
    chosen = """filter(from_json(
        details:planning_information.technique_information,
        'ARRAY<STRUCT<maintenance_type STRING, is_chosen BOOLEAN>>'),
        x -> x.is_chosen)[0].maintenance_type"""
    plans = {r.f: r.t for r in planned.selectExpr(
        'origin.flow_name AS f', f'{chosen} AS t').collect()}
    for d in sorted(r.name for r in datasets if r.name.count('.') == 2):
        rows = spark.table(d).count()
        how = (plans.get(d) or '').removeprefix('MAINTENANCE_TYPE_').lower()
        how = f'  ({how})' if how else ''  # how a materialized view refreshed
        print(f"  {d.replace('globalbank_dev.', ''):<36}{rows:>9,} rows{how}")
'''

BRONZE = """\"\"\"Bronze, declared: every source's files, once each, as received.\"\"\"
from pyspark import pipelines as dp
from pyspark.sql import functions as F

KEEP = {'pipelines.reset.allowed': 'false'}  # a full refresh never empties it


def landed(source, fmt, hints):
    return (spark.readStream.format('cloudFiles')
            .option('cloudFiles.format', fmt)
            .option('cloudFiles.schemaHints', hints)
            .option('header', 'true')
            .load(f'/Volumes/globalbank_dev/landing/{source}/')
            .withColumn('source_file', F.col('_metadata.file_path'))
            .withColumn('landed_at',
                        F.col('_metadata.file_modification_time')))


@dp.table(name='globalbank_dev.bronze.card_auths', table_properties=KEEP)
def card_auths():
    return landed('card_auths', 'json',
                  'amount DECIMAL(18,2), auth_ts TIMESTAMP')


@dp.table(name='globalbank_dev.bronze.core_cdc', table_properties=KEEP)
def core_cdc():
    return landed('core_cdc', 'json', 'seq BIGINT, ts TIMESTAMP')
"""

SILVER_MV = """\"\"\"Silver, declared: one row per real thing.\"\"\"
from pyspark import pipelines as dp


@dp.materialized_view(name='globalbank_dev.silver.card_transactions')
def card_transactions():
    return spark.sql(\"\"\"
        SELECT * EXCEPT (_rescued_data, landed_at)
        FROM globalbank_dev.bronze.card_auths
        QUALIFY row_number() OVER (PARTITION BY auth_id
                                   ORDER BY landed_at) = 1\"\"\")
"""

GOLD = """\"\"\"Gold, declared: products for the business, read from silver only.\"\"\"
from pyspark import pipelines as dp


@dp.materialized_view(name='globalbank_dev.gold.card_spend_daily')
def card_spend_daily():
    return spark.sql(\"\"\"
        SELECT to_date(auth_ts) AS day, count(*) AS auths,
               sum(amount) AS spend
        FROM globalbank_dev.silver.card_transactions
        WHERE status = 'APPROVED' AND currency = 'EUR'
        GROUP BY ALL\"\"\")
"""

RULES = """
RULES = {  # a row that breaks one is dropped from silver, and kept aside
    'amount_known': 'amount IS NOT NULL',
    'amount_in_range': 'amount > 0 AND amount <= 1000',
}
"""

SILVER_EXPECT = """\"\"\"Silver, declared: one row per real thing, checked.\"\"\"
from pyspark import pipelines as dp
""" + RULES + """

@dp.materialized_view(name='globalbank_dev.silver.card_transactions')
@dp.expect('currency_known', "currency IN ('EUR', 'USD', 'GBP', 'CHF')")
@dp.expect_all_or_drop(RULES)
def card_transactions():
    return spark.sql(\"\"\"
        SELECT * EXCEPT (_rescued_data, landed_at)
        FROM globalbank_dev.bronze.card_auths
        QUALIFY row_number() OVER (PARTITION BY auth_id
                                   ORDER BY landed_at) = 1\"\"\")
"""

QUARANTINE = """

@dp.materialized_view(name='globalbank_dev.silver.card_transactions_quarantine')
def card_transactions_quarantine():
    broken = ' OR '.join(f'NOT coalesce({rule}, false)'
                         for rule in RULES.values())
    return spark.sql(f\"\"\"
        SELECT *, _rescued_data AS rescued
        FROM globalbank_dev.bronze.card_auths WHERE {broken}\"\"\")
"""

CDC = """

CUSTOMER = ('customer_id STRING, first_name STRING, last_name STRING,'
            ' national_id STRING, date_of_birth DATE, email STRING,'
            ' address STRING, region STRING, branch_id STRING,'
            ' segment STRING, kyc_status STRING, customer_since DATE')


@dp.temporary_view()
def customer_changes():
    return spark.sql(f\"\"\"
        SELECT op, seq, ts, c.*
        FROM (SELECT op, seq, ts, from_json(after, '{CUSTOMER}') AS c
              FROM STREAM(globalbank_dev.bronze.core_cdc)
              WHERE `table` = 'customers')\"\"\")


# Course 5's MERGE, out-of-order guard and all, as one declaration each.
dp.create_streaming_table('globalbank_dev.silver.customers')
dp.create_auto_cdc_flow(
    target='globalbank_dev.silver.customers', source='customer_changes',
    keys=['customer_id'], sequence_by='seq', apply_as_deletes="op = 'D'",
    except_column_list=['op', 'ts'], stored_as_scd_type=1)

dp.create_streaming_table('globalbank_dev.silver.customers_history')
dp.create_auto_cdc_flow(
    target='globalbank_dev.silver.customers_history', source='customer_changes',
    keys=['customer_id'], sequence_by='seq', except_column_list=['op'],
    stored_as_scd_type=2, track_history_column_list=['address', 'kyc_status'])
"""

GRAPH = '''"""The pipeline's graph, as its last update declared it: what reads what."""
from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark

pipeline = next(WorkspaceClient().pipelines.list_pipelines(
    filter=f"name LIKE '{NAME}'"))
edges = get_spark().sql(f"""
    SELECT details:flow_definition.output_dataset AS target,
           explode(from_json(details:flow_definition.input_datasets,
                             'ARRAY<STRING>')) AS source
    FROM event_log('{pipeline.pipeline_id}')
    WHERE event_type = 'flow_definition' AND origin.update_id = (
        SELECT origin.update_id FROM event_log('{pipeline.pipeline_id}')
        WHERE event_type = 'create_update' ORDER BY timestamp DESC LIMIT 1)
    ORDER BY target, source""").collect()
short = lambda name: name.replace('globalbank_dev.', '')
for e in edges:
    print(f'{short(e.source):<26} -> {short(e.target)}')
'''

QUALITY = '''"""What each expectation passed and failed in the last update."""
from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark

pipeline = next(WorkspaceClient().pipelines.list_pipelines(
    filter=f"name LIKE '{NAME}'"))
rows = get_spark().sql(f"""
    SELECT e.name, e.passed_records AS passed, e.failed_records AS failed
    FROM (SELECT explode(from_json(
              details:flow_progress.data_quality.expectations,
              'ARRAY<STRUCT<name STRING, passed_records BIGINT,
                            failed_records BIGINT>>')) AS e
          FROM event_log('{pipeline.pipeline_id}')
          WHERE event_type = 'flow_progress' AND origin.update_id = (
              SELECT origin.update_id FROM event_log('{pipeline.pipeline_id}')
              WHERE event_type = 'create_update'
              ORDER BY timestamp DESC LIMIT 1))
    ORDER BY e.name""").collect()
for r in rows:
    print(f'{r.name:<18} passed {r.passed:>7,}   failed {r.failed:>4,}')
'''

RECON = '''"""Silver, reconciled: every bronze row is kept, resent or quarantined."""
from globalbank.session import get_spark

spark = get_spark()
n = lambda sql: spark.sql(sql).first()[0]
bronze = n('SELECT count(*) FROM globalbank_dev.bronze.card_auths')
silver = n('SELECT count(*) FROM globalbank_dev.silver.card_transactions')
held = n('SELECT count(*) FROM'
         ' globalbank_dev.silver.card_transactions_quarantine')
resent = n("""SELECT count(*) - count(DISTINCT auth_id)
              FROM globalbank_dev.bronze.card_auths""")
print(f'bronze      {bronze:>7,}')
print(f'silver      {silver:>7,}')
print(f'quarantine  {held:>7,}')
print(f'resends     {resent:>7,}')
print(f'{silver:,} + {held:,} + {resent:,} = {silver + held + resent:,}'
      f" {'=' if silver + held + resent == bronze else '!='} {bronze:,}")
'''

EVENTS = '''"""The last update, from the event log: each flow, its status, its duration."""
from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark

pipeline = next(WorkspaceClient().pipelines.list_pipelines(
    filter=f"name LIKE '{NAME}'"))
spark = get_spark()
log = f"event_log('{pipeline.pipeline_id}')"
spark.sql(f"""SELECT * FROM {log} WHERE origin.update_id = (
    SELECT origin.update_id FROM {log} WHERE event_type = 'create_update'
    ORDER BY timestamp DESC LIMIT 1)""").createOrReplaceTempView('last_update')
kinds = spark.sql("""SELECT event_type, count(*) AS n FROM last_update
                     GROUP BY ALL ORDER BY n DESC LIMIT 4""").collect()
print('events:', ', '.join(f'{k.event_type} {k.n}' for k in kinds))
for f in spark.sql("""
        SELECT origin.flow_name AS flow,
               max_by(details:flow_progress.status, timestamp) AS status,
               timestampdiff(SECOND, min(timestamp), max(timestamp)) AS secs
        FROM last_update WHERE event_type = 'flow_progress'
        GROUP BY ALL ORDER BY flow""").collect():
    flow = f.flow.replace('globalbank_dev.', '')
    print(f'  {flow:<38}{f.status:<11}{f.secs:>4}s')
'''

COUNTS = '''"""Rows per table, bronze to gold."""
from globalbank.session import get_spark

spark = get_spark()
for t in ['bronze.card_auths', 'bronze.core_cdc', 'silver.card_transactions',
          'silver.customers', 'gold.card_spend_daily']:
    print(f'  {t:<28}{spark.table(f"globalbank_dev.{t}").count():>8,} rows')
'''

PIPE = [RESET, CAT]
DEP = 'python -m globalbank.deploy'
RUN1 = 'python -m globalbank.run'
LAND1 = ['bash land.sh 2026-10-01 > /dev/null', 'bash land.sh 2026-09-01 core_cdc 2026-10-01 > /dev/null']
LAND_ALL = ['bash land.sh 2026-10-13 card_auths 2026-10-14 > /dev/null', 'bash land.sh 2026-10-20 > /dev/null',
            'bash land.sh 2026-09-01 core_cdc 2026-10-20 > /dev/null']
q = lambda c: c + ' > /dev/null'

step(P, '01-why-declare', PARENT, ['nightly.sh'], {'nightly.sh': NIGHTLY},
     ['bash nightly.sh 2026-10-02', 'python -m globalbank.ledger post 2026-10-02'],
     PIPE + LAND1 + [q('python -m globalbank.land'), q('python -m globalbank.land core_cdc'),
                     q('python -m globalbank.ledger post 2026-10-01'), q("python -m globalbank.cdc customers '2026-'")])
step(P, '02-streaming-tables', f'{P}/01-why-declare', ['globalbank/deploy.py', 'globalbank/run.py', 'pipelines/bronze.py'],
     {'globalbank/deploy.py': DEPLOY, 'globalbank/run.py': RUN, 'pipelines/bronze.py': BRONZE},
     [DEP, RUN1, 'bash land.sh 2026-10-02 | wc -l', RUN1], PIPE + LAND1)
step(P, '03-materialized-views', f'{P}/02-streaming-tables', ['pipelines/silver.py', 'pipelines/gold.py'],
     {'pipelines/silver.py': SILVER_MV, 'pipelines/gold.py': GOLD},
     [DEP, RUN1, 'bash land.sh 2026-10-02 > /dev/null', RUN1], PIPE + LAND1)
step(P, '04-graph', f'{P}/03-materialized-views', ['globalbank/graph.py'], {'globalbank/graph.py': GRAPH},
     ['python -m globalbank.graph'], PIPE + LAND1 + [q(DEP), q(RUN1)])
step(P, '05-expectations', f'{P}/04-graph', ['pipelines/silver.py', 'globalbank/quality.py'],
     {'pipelines/silver.py': SILVER_EXPECT, 'globalbank/quality.py': QUALITY},
     [DEP, RUN1, 'python -m globalbank.quality'], PIPE + LAND_ALL)
step(P, '06-quarantine', f'{P}/05-expectations', ['pipelines/silver.py', 'globalbank/recon.py'],
     {'pipelines/silver.py': SILVER_EXPECT + QUARANTINE, 'globalbank/recon.py': RECON},
     [RUN1, 'python -m globalbank.recon'], PIPE + LAND_ALL + [q(DEP)])
step(P, '07-auto-cdc', f'{P}/06-quarantine', ['pipelines/silver.py'],
     {'pipelines/silver.py': SILVER_EXPECT + QUARANTINE + CDC},
     [RUN1, 'python -m globalbank.customer C000001'], PIPE + LAND_ALL + [q(DEP)])
step(P, '08-event-log', f'{P}/07-auto-cdc', ['globalbank/events.py'], {'globalbank/events.py': EVENTS},
     ['python -m globalbank.events'], PIPE + LAND_ALL + [q(DEP), q(RUN1)], extra={'volatile': ['digits']})
step(P, '09-full-refresh', f'{P}/08-event-log', ['globalbank/counts.py'], {'globalbank/counts.py': COUNTS},
     ['python -m globalbank.counts', RUN1 + ' --full-refresh', 'python -m globalbank.counts'],
     PIPE + LAND_ALL + [q(DEP), q(RUN1)])
print('built')
