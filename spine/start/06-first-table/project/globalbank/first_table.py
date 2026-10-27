"""The first bronze table: a day of card authorizations, from the volume."""
from globalbank.session import get_spark

SOURCE = '/Volumes/globalbank_dev/landing/card_auths/2026-10-01'
TABLE = 'globalbank_dev.bronze.card_auths'

spark = get_spark()
auths = spark.read.json(SOURCE)
auths.write.saveAsTable(TABLE)

print(spark.table(TABLE).count(), 'rows in', TABLE)
print('amount is', dict(auths.dtypes)['amount'])
(spark.sql(f'DESCRIBE HISTORY {TABLE}')
    .select('version', 'operation', 'operationMetrics.numOutputRows')
    .show(truncate=False))
