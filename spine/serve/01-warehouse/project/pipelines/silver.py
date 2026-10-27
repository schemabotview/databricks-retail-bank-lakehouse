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


CUSTOMER = ('customer_id STRING, first_name STRING, last_name STRING,'
            ' national_id STRING, date_of_birth DATE, email STRING,'
            ' address STRING, region STRING, branch_id STRING,'
            ' segment STRING, kyc_status STRING, customer_since DATE')


@dp.temporary_view()
def customer_changes():
    return spark.sql(f"""
        SELECT op, seq, ts, c.*
        FROM (SELECT op, seq, ts, from_json(after, '{CUSTOMER}') AS c
              FROM STREAM(globalbank_dev.bronze.core_cdc)
              WHERE `table` = 'customers')""")


# Course 5's MERGE, out-of-order guard and all, as one declaration each.
dp.create_streaming_table('globalbank_dev.silver.customers')
dp.create_auto_cdc_flow(
    target='globalbank_dev.silver.customers', source='customer_changes',
    keys=['customer_id'], sequence_by='seq', apply_as_deletes="op = 'D'",
    except_column_list=['op', 'ts'], stored_as_scd_type=1)

dp.create_streaming_table('globalbank_dev.silver.customers_history')
dp.create_auto_cdc_flow(
    target='globalbank_dev.silver.customers_history', source='customer_changes',
    keys=['customer_id'], sequence_by='seq', except_column_list=['op'],
    stored_as_scd_type=2, track_history_column_list=['address', 'kyc_status'])
