"""Land card authorizations in bronze with Auto Loader: every file once."""
import re

from pyspark.errors import StreamingQueryException
from pyspark.sql import functions as F

from globalbank.session import get_spark

SOURCE = '/Volumes/globalbank_dev/landing/card_auths/'
CHECKPOINT = '/Volumes/globalbank_dev/bronze/checkpoints/card_auths'
TABLE = 'globalbank_dev.bronze.card_auths'
HINTS = 'amount DECIMAL(18,2), auth_ts TIMESTAMP'


def ingest(spark):
    auths = (spark.readStream.format('cloudFiles')
             .option('cloudFiles.format', 'json')
             .option('cloudFiles.schemaLocation', CHECKPOINT)
             .option('cloudFiles.schemaHints', HINTS)
             .load(SOURCE)
             .withColumn('source_file', F.col('_metadata.file_path'))
             .withColumn('landed_at',
                         F.col('_metadata.file_modification_time')))
    query = (auths.writeStream
             .option('checkpointLocation', CHECKPOINT)
             .option('mergeSchema', 'true')
             .trigger(availableNow=True)
             .toTable(TABLE))
    query.awaitTermination()


if __name__ == '__main__':
    spark = get_spark()
    exists = spark.catalog.tableExists(TABLE)
    before = spark.table(TABLE).count() if exists else 0
    try:
        ingest(spark)
    except StreamingQueryException as e:
        reason = re.search(r'\[(UNKNOWN_FIELD_EXCEPTION[\w.]*)\]', str(e))
        found = re.search(r'Rescued record schema: (.*?) SQLSTATE', str(e))
        print('stream stopped:', reason.group(1) if reason else 'failed')
        print('new column:', found.group(1) if found else '?')
        raise SystemExit(1)
    after = spark.table(TABLE).count()
    print(f'{TABLE}: {before:,} + {after - before:,} = {after:,} rows')
