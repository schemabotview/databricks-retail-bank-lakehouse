"""What the lakehouse has cost here, in DBUs, from the bill itself."""
from globalbank.session import get_spark

spark = get_spark()
rows = spark.sql("""
    SELECT billing_origin_product AS product,
           round(sum(usage_quantity), 2) AS dbus, max(usage_end_time) AS last
    FROM system.billing.usage
    WHERE usage_date >= DATE'2026-10-27'  -- the course on this workspace
    GROUP BY ALL ORDER BY dbus DESC""").collect()
print(f'{sum(r.dbus for r in rows):.2f} DBUs since 27 October,'
      f' billed up to {max(r.last for r in rows):%d %b %H:%M}:')
for r in rows:
    print(f'  {r.product:<26}{r.dbus:>8.2f}')
