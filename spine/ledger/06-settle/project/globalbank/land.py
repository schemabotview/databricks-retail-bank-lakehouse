"""Land a source in bronze with Auto Loader: every file once."""
import re
import sys

from pyspark.errors import StreamingQueryException
from pyspark.sql import functions as F

from globalbank.session import get_spark

SOURCES = {
    'card_auths': ('json', 'amount DECIMAL(18,2), auth_ts TIMESTAMP'),
    'settlements': ('csv', 'amount DECIMAL(18,2), amount_eur DECIMAL(18,2),'
                           ' cleared_date DATE'),
}


def ingest(spark, source):
    fmt, hints = SOURCES[source]
    checkpoint = f'/Volumes/globalbank_dev/bronze/checkpoints/{source}'
    rows = (spark.readStream.format('cloudFiles')
            .option('cloudFiles.format', fmt)
            .option('cloudFiles.schemaLocation', checkpoint)
            .option('cloudFiles.schemaHints', hints)
            .option('header', 'true')  # CSV: line 1 names the columns
            .load(f'/Volumes/globalbank_dev/landing/{source}/')
            .withColumn('source_file', F.col('_metadata.file_path'))
            .withColumn('landed_at',
                        F.col('_metadata.file_modification_time')))
    query = (rows.writeStream
             .option('checkpointLocation', checkpoint)
             .option('mergeSchema', 'true')
             .trigger(availableNow=True)
             .toTable(f'globalbank_dev.bronze.{source}'))
    query.awaitTermination()


if __name__ == '__main__':
    source = sys.argv[1] if len(sys.argv) > 1 else 'card_auths'
    table = f'globalbank_dev.bronze.{source}'
    spark = get_spark()
    exists = spark.catalog.tableExists(table)
    before = spark.table(table).count() if exists else 0
    try:
        ingest(spark, source)
    except StreamingQueryException as e:
        reason = re.search(r'\[(UNKNOWN_FIELD_EXCEPTION[\w.]*)\]', str(e))
        found = re.search(r'Rescued record schema: (.*?) SQLSTATE', str(e))
        print('stream stopped:', reason.group(1) if reason else 'failed')
        print('new column:', found.group(1) if found else '?')
        raise SystemExit(1)
    after = spark.table(table).count()
    print(f'{table}: {before:,} + {after - before:,} = {after:,} rows')
