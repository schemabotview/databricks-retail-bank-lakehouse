"""Silver, declared: one row per real thing, checked."""
from pyspark import pipelines as dp

RULES = {  # a row that breaks one is dropped from silver, and kept aside
    'amount_known': 'amount IS NOT NULL',
    'amount_in_range': 'amount > 0 AND amount <= 1000',
}


@dp.materialized_view(name='globalbank_dev.silver.card_transactions')
@dp.expect('currency_known', "currency IN ('EUR', 'USD', 'GBP', 'CHF')")
@dp.expect_all_or_drop(RULES)
def card_transactions():
    return spark.sql("""
        SELECT * EXCEPT (_rescued_data, landed_at)
        FROM globalbank_dev.bronze.card_auths
        QUALIFY row_number() OVER (PARTITION BY auth_id
                                   ORDER BY landed_at) = 1""")


@dp.materialized_view(name='globalbank_dev.silver.card_transactions_quarantine')
def card_transactions_quarantine():
    broken = ' OR '.join(f'NOT coalesce({rule}, false)'
                         for rule in RULES.values())
    return spark.sql(f"""
        SELECT *, _rescued_data AS rescued
        FROM globalbank_dev.bronze.card_auths WHERE {broken}""")
