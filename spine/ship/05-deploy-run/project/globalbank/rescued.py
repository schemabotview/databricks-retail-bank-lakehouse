"""Rows whose fields did not fit the schema: kept, in _rescued_data."""
from pyspark.sql import functions as F

from globalbank.session import get_spark

TABLE = 'globalbank_dev.bronze.card_auths'

spark = get_spark()
(spark.table(TABLE)
    .where(F.col('_rescued_data').isNotNull())
    .select('auth_id', 'amount',
            F.get_json_object('_rescued_data', '$.amount').alias('rescued'))
    .orderBy('auth_id')
    .show())
