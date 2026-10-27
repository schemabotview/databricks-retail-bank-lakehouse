"""The rule as a stream: 10-minute windows over bronze, flags into gold."""
from pyspark.sql import functions as F

from globalbank.session import get_spark

FLAGS = 'globalbank_dev.gold.fraud_flags'
CHECKPOINT = '/Volumes/globalbank_dev/bronze/checkpoints/fraud_flags'

spark = get_spark()
flags = (spark.readStream.table('globalbank_dev.bronze.card_auths')
         .withWatermark('auth_ts', '30 minutes')
         .groupBy(F.window('auth_ts', '10 minutes', '5 minutes'), 'card_id')
         .agg(F.count('*').alias('auths'), F.sum('amount').alias('total'))
         .where('auths > 5'))
query = (flags.writeStream.outputMode('append')
         .option('checkpointLocation', CHECKPOINT)
         .trigger(availableNow=True).toTable(FLAGS))
query.awaitTermination()
for f in spark.table(FLAGS).orderBy('window').collect():
    print(f"{f.window.start:%d %b %H:%M}-{f.window.end:%H:%M}  {f.card_id}"
          f"  {f.auths} auths  {f.total} EUR")
