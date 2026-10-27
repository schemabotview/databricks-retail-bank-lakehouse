"""Features per authorization, in Unity Catalog: what the model sees."""
from globalbank.session import get_spark

FEATURES = 'globalbank_dev.ml.card_features'

spark = get_spark()
spark.sql(f"""CREATE OR REPLACE TABLE {FEATURES} AS
    SELECT auth_id, card_id, auth_ts, to_date(auth_ts) AS day,
           count(*) OVER (PARTITION BY card_id ORDER BY auth_ts
                          RANGE BETWEEN INTERVAL 10 MINUTES PRECEDING
                                    AND CURRENT ROW) AS auths_10m,
           cast(entry_mode = 'online' AS INT) AS online,
           cast(amount < 2 AS INT) AS tiny_amount,
           cast(hour(auth_ts) < 5 AS INT) AS night,
           cast(auth_id IN (SELECT auth_id
                            FROM globalbank_dev.silver.chargebacks)
                AS INT) AS fraud
    FROM globalbank_dev.silver.card_transactions""")
print(f'{FEATURES}: {spark.table(FEATURES).count():,} rows')
spark.sql(f"""SELECT day, count(*) AS auths, sum(fraud) AS fraud,
                     round(avg(auths_10m), 2) AS avg_auths_10m
              FROM {FEATURES} GROUP BY day ORDER BY day""").show()
