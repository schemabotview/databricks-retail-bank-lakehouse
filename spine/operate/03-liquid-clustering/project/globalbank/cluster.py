"""Liquid clustering: the same query on the same rows, laid out two ways."""
import time

from databricks.sdk import WorkspaceClient

from globalbank.session import get_spark
from globalbank.warehouse import run

BRONZE = 'globalbank_dev.bronze.card_auths'
QUERY = """SELECT count(*), sum(amount) FROM {} WHERE merchant_id = 'M0001'
           AND to_date(auth_ts) = '2026-10-03'"""
SMALL = "TBLPROPERTIES ('delta.targetFileSize' = '128kb')"  # files to skip
spark = get_spark()
for name, layout in (('by_arrival', ''), ('clustered',
                                          'CLUSTER BY (merchant_id, auth_ts)')):
    spark.sql(f"""CREATE OR REPLACE TABLE globalbank_dev.silver.auths_{name}
                  {layout} {SMALL} AS SELECT * FROM {BRONZE}""")
    spark.sql(f'OPTIMIZE globalbank_dev.silver.auths_{name}')
w = WorkspaceClient()
for name in ('by_arrival', 'clustered'):
    run(w, QUERY.format(f'globalbank_dev.silver.auths_{name}'))
for _ in range(40):  # the query history arrives some minutes later
    _, rows = run(w, """
        SELECT regexp_extract(statement_text, 'auths_([a-z_]+)', 1) AS t,
               read_files, pruned_files
        FROM system.query.history
        WHERE statement_text LIKE '%M0001%auths_%'
          AND statement_text NOT LIKE '%system.query%'
          AND start_time > current_timestamp() - INTERVAL 30 MINUTES
        ORDER BY start_time DESC LIMIT 2""")
    if len(rows) == 2:
        break
    time.sleep(30)
for t, read, pruned in sorted(rows):
    print(f'silver.auths_{t:<11} files read {read:>3}, skipped {pruned:>3}')
