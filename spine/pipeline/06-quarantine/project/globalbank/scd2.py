"""Silver customers_history: every version of each customer (SCD type 2)."""
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
