"""The change data feed: what the last version did, row by row."""
from globalbank.session import get_spark

SILVER = 'globalbank_dev.silver.card_transactions'

spark = get_spark()
last = spark.sql(f'DESCRIBE HISTORY {SILVER} LIMIT 1').first().version
changes = spark.sql(f"SELECT * FROM table_changes('{SILVER}', {last})")
changes.groupBy('_change_type').count().orderBy('_change_type').show()
(changes.where("_change_type LIKE 'update%'")
    .select('auth_id', '_change_type', 'status', 'settled_eur')
    .orderBy('auth_id', '_change_type')
    .show(4))
