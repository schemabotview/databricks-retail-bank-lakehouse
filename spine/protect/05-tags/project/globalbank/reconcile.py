"""Reconcile bronze with the volume: every file, every line, counted."""
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
