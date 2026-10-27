"""Silver card_transactions: bronze's authorizations, one row per auth_id."""
import sys

from globalbank.session import get_spark

BRONZE = 'globalbank_dev.bronze.card_auths'
SILVER = 'globalbank_dev.silver.card_transactions'


def create(spark):
    spark.sql(f"""CREATE TABLE IF NOT EXISTS {SILVER} (
        auth_id STRING NOT NULL, card_id STRING, merchant_id STRING,
        mcc STRING, amount DECIMAL(18,2), currency STRING,
        auth_ts TIMESTAMP, status STRING, source_file STRING,
        settled_eur DECIMAL(18,2), cleared_date DATE)""")


def post(spark, day):
    """Merge one day of authorizations: a resent one is inserted once."""
    spark.sql(f"""MERGE INTO {SILVER} t
        USING (SELECT * FROM {BRONZE} WHERE to_date(auth_ts) = '{day}'
               QUALIFY row_number() OVER (PARTITION BY auth_id
                                          ORDER BY landed_at) = 1) s
        ON t.auth_id = s.auth_id
        WHEN NOT MATCHED THEN INSERT (auth_id, card_id, merchant_id, mcc,
            amount, currency, auth_ts, status, source_file)
        VALUES (s.auth_id, s.card_id, s.merchant_id, s.mcc, s.amount,
            s.currency, s.auth_ts, s.status, s.source_file)""")


if __name__ == '__main__':
    spark = get_spark()
    create(spark)
    verb, day = sys.argv[1], sys.argv[2]
    {'post': post}[verb](spark, day)
    print(f'{SILVER}: {spark.table(SILVER).count():,} rows')
