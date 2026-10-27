"""What the last MERGE did to the files: rewrite, or mark."""
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
