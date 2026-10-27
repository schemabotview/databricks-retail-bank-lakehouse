"""Rows per table, bronze to gold."""
from globalbank.session import get_spark

spark = get_spark()
for t in ['bronze.card_auths', 'silver.card_transactions',
          'silver.customers', 'gold.card_spend_daily']:
    print(f'  {t:<28}{spark.table(f"globalbank_dev.{t}").count():>8,} rows')
