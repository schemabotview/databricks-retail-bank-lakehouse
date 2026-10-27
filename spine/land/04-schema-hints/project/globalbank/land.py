"""Land card authorizations in bronze with Auto Loader: every file once."""
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
             .load(SOURCE))
    query = (auths.writeStream
             .option('checkpointLocation', CHECKPOINT)
             .trigger(availableNow=True)
             .toTable(TABLE))
    query.awaitTermination()


if __name__ == '__main__':
    spark = get_spark()
    exists = spark.catalog.tableExists(TABLE)
    before = spark.table(TABLE).count() if exists else 0
    ingest(spark)
    after = spark.table(TABLE).count()
    print(f'{TABLE}: {before:,} + {after - before:,} = {after:,} rows')
