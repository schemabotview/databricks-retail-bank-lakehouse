"""Customers per region, as the current user is allowed to see them."""
from globalbank.session import get_spark

spark = get_spark()
rows = spark.sql("""SELECT region, count(*) AS n
                    FROM globalbank_dev.silver.customers
                    GROUP BY region ORDER BY region""").collect()
print('  '.join(f'{r.region} {r.n:,}' for r in rows) or 'no rows')
