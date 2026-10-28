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
print('night   windows  cards  first  last   most in a window')
for r in spark.sql(f"""SELECT to_date(window.start) AS night,
        count(*) AS windows, count(DISTINCT card_id) AS cards,
        date_format(min(window.start), 'HH:mm') AS first,
        date_format(max(window.end), 'HH:mm') AS last, max(auths) AS most
        FROM {FLAGS} GROUP BY ALL ORDER BY night""").collect():
    print(f'{r.night:%d %b}  {r.windows:>7}  {r.cards:>5}  {r.first}  {r.last}'
          f'  {r.most:>16}')
