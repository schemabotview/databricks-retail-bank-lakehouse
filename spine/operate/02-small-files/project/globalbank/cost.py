"""This week's cost in DBUs by product, from the bill itself."""
from globalbank.session import get_spark

spark = get_spark()
rows = spark.sql("""
    SELECT billing_origin_product AS product, sku_name,
           round(sum(usage_quantity), 2) AS dbus
    FROM system.billing.usage
    WHERE usage_date >= current_date() - INTERVAL 7 DAYS
    GROUP BY ALL ORDER BY dbus DESC""").collect()
print(f'{sum(r.dbus for r in rows):.2f} DBUs in 7 days, by product:')
for r in rows[:8]:
    print(f'  {r.product:<20}{r.sku_name[:38]:<40}{r.dbus:>8.2f}')
