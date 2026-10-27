"""Bronze, declared: every source's files, once each, as received."""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

KEEP = {'pipelines.reset.allowed': 'false'}  # a full refresh never empties it


def landed(source, fmt, hints):
    return (spark.readStream.format('cloudFiles')
            .option('cloudFiles.format', fmt)
            .option('cloudFiles.schemaHints', hints)
            .option('header', 'true')
            .load(f'/Volumes/globalbank_dev/landing/{source}/')
            .withColumn('source_file', F.col('_metadata.file_path'))
            .withColumn('landed_at',
                        F.col('_metadata.file_modification_time')))


@dp.table(name='globalbank_dev.bronze.card_auths', table_properties=KEEP)
def card_auths():
    return landed('card_auths', 'json',
                  'amount DECIMAL(18,2), auth_ts TIMESTAMP')


@dp.table(name='globalbank_dev.bronze.core_cdc', table_properties=KEEP)
def core_cdc():
    return landed('core_cdc', 'json', 'seq BIGINT, ts TIMESTAMP')
