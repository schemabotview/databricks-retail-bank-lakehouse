"""Two customers, as the current user is allowed to see them."""
from globalbank.session import get_spark

spark = get_spark()
for r in spark.sql("""
        SELECT c.customer_id, c.national_id, a.iban
        FROM globalbank_dev.silver.customers c
        JOIN globalbank_dev.silver.accounts a USING (customer_id)
        WHERE a.product = 'current'
        ORDER BY c.customer_id LIMIT 2""").collect():
    print(f'{r.customer_id}  national_id {r.national_id:<12} iban {r.iban}')
