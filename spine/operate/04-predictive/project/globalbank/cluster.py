"""Liquid clustering: the same query on the same rows, laid out two ways."""
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
    SELECT regexp_extract(statement_text, 'auths_(\\w+)', 1) AS t,
           read_files, pruned_files
    FROM system.query.history
    WHERE statement_text LIKE '%M0001%auths_%'
      AND start_time > current_timestamp() - INTERVAL 15 MINUTES
    ORDER BY start_time DESC LIMIT 2""")
for t, read, pruned in sorted(rows):
    print(f'silver.auths_{t:<11} files read {read:>3}, skipped {pruned:>3}')
