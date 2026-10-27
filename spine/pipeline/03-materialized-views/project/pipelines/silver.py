"""Silver, declared: one row per real thing."""
from pyspark import pipelines as dp


@dp.materialized_view(name='globalbank_dev.silver.card_transactions')
def card_transactions():
    return spark.sql("""
        SELECT * EXCEPT (_rescued_data, landed_at)
        FROM globalbank_dev.bronze.card_auths
        QUALIFY row_number() OVER (PARTITION BY auth_id
                                   ORDER BY landed_at) = 1""")
