"""Where each row came from: its file, and when that file landed."""
from pyspark.sql import functions as F

from globalbank.session import get_spark

TABLE = 'globalbank_dev.bronze.card_auths'

spark = get_spark()
(spark.table(TABLE)
    .groupBy(F.element_at(F.split('source_file', '/'), -1).alias('file'),
             'landed_at')
    .count()
    .orderBy(F.desc('count'), 'file')
    .show(3, truncate=False))
