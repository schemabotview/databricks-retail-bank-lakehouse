"""The change data feed: what the last MERGE did, row by row."""
from globalbank.session import get_spark

SILVER = 'globalbank_dev.silver.card_transactions'

spark = get_spark()
last = spark.sql(f'DESCRIBE HISTORY {SILVER}') \
    .where("operation = 'MERGE'").agg({'version': 'max'}).first()[0]
changes = spark.sql(f"SELECT * FROM table_changes('{SILVER}', {last})")
counts = changes.groupBy('_change_type').count().orderBy('_change_type')
print(f'version {last}:',
      ', '.join(f'{r[0]} {r[1]:,}' for r in counts.collect()))
for r in (changes.where("_change_type LIKE 'update%'")
          .orderBy('auth_id', '_change_type').limit(4).collect()):
    print(f'  {r.auth_id}  {r._change_type:<18}{r.status:<10}{r.settled_eur}')
