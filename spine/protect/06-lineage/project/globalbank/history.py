"""A table's history: one row per version, with what wrote it."""
import sys

from pyspark.sql import functions as F

from globalbank.session import get_spark

spark = get_spark()
history = (spark.sql(f'DESCRIBE HISTORY {sys.argv[1]}')
           .select('version', 'operation',
                   F.coalesce(F.col('operationMetrics.numTargetRowsInserted'),
                              F.col('operationMetrics.numOutputRows'),
                              F.lit('')).alias('rows'))
           .orderBy('version'))
for r in history.collect():
    print(f'version {r.version:<3}{r.operation:<20}{r.rows:>6}')
