"""Silver card_transactions: bronze's authorizations, one row per auth_id."""
import re
import sys

from globalbank.session import get_spark

BRONZE = 'globalbank_dev.bronze.card_auths'
SILVER = 'globalbank_dev.silver.card_transactions'
CLEARING = 'globalbank_dev.bronze.settlements'


def create(spark):
    spark.sql(f"""CREATE TABLE IF NOT EXISTS {SILVER} (
        auth_id STRING NOT NULL, card_id STRING, merchant_id STRING,
        mcc STRING, amount DECIMAL(18,2), currency STRING,
        auth_ts TIMESTAMP, status STRING, source_file STRING,
        settled_eur DECIMAL(18,2), cleared_date DATE)""")
    constraints = spark.sql(f'SHOW TBLPROPERTIES {SILVER}').collect()
    if not any(r.key == 'delta.constraints.amount_in_range'
               for r in constraints):
        # An illustrative per-authorization limit, not a real card rule.
        spark.sql(f"""ALTER TABLE {SILVER} ADD CONSTRAINT amount_in_range
                       CHECK (amount > 0 AND amount <= 1000)""")
    spark.sql(f"""ALTER TABLE {SILVER}
                   SET TBLPROPERTIES (delta.enableChangeDataFeed = true)""")


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


def settle(spark, day):
    """Apply one day's clearing file: settled, or reversed."""
    spark.sql(f"""MERGE INTO {SILVER} t
        USING (SELECT * FROM {CLEARING} WHERE cleared_date = '{day}') s
        ON t.auth_id = s.auth_id
        WHEN MATCHED THEN UPDATE SET
            status = IF(s.kind = 'REVERSAL', 'REVERSED', 'SETTLED'),
            settled_eur = s.amount_eur, cleared_date = s.cleared_date""")


if __name__ == '__main__':
    spark = get_spark()
    create(spark)
    verb, day = sys.argv[1], sys.argv[2]
    try:
        {'post': post, 'settle': settle}[verb](spark, day)
    except Exception as e:
        reason = re.search(r'\[(DELTA_\w+)\]', str(e))
        print('refused:', reason.group(1) if reason else type(e).__name__)
        print(str(e).split('\n')[1].strip()[:72])
        raise SystemExit(1)
    print(f'{SILVER}: {spark.table(SILVER).count():,} rows')
