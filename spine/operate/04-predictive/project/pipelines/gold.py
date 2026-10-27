"""Gold, declared: products for the business, read from silver only."""
from pyspark import pipelines as dp


@dp.materialized_view(name='globalbank_dev.gold.card_spend_daily')
def card_spend_daily():
    return spark.sql("""
        SELECT to_date(auth_ts) AS day, count(*) AS auths,
               sum(amount) AS spend
        FROM globalbank_dev.silver.card_transactions
        WHERE status = 'APPROVED' AND currency = 'EUR'
        GROUP BY ALL""")
