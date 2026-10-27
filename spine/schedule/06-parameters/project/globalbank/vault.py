"""The PII vault: identifying columns, keyed by customer_id, kept apart."""
from globalbank.session import get_spark

VAULT = 'globalbank_dev.vault.customer_pii'

spark = get_spark()
spark.sql(f"""CREATE OR REPLACE TABLE {VAULT} AS
    SELECT customer_id, first_name, last_name, national_id,
           date_of_birth, email, address
    FROM globalbank_dev.silver.customers""")
print(f'{VAULT}: {spark.table(VAULT).count():,} customers')
