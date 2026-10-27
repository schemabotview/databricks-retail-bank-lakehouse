"""Who touched silver.customers in the last hour, from the audit log."""
from globalbank.session import get_spark

spark = get_spark()
rows = spark.sql("""
    SELECT user_identity.email AS who, action_name, count(*) AS n
    FROM system.access.audit
    WHERE service_name = 'unityCatalog'
      AND request_params.full_name_arg = 'globalbank_dev.silver.customers'
      AND event_time > current_timestamp() - INTERVAL 1 HOUR
    GROUP BY ALL ORDER BY n DESC""").collect()
print(f'{len(rows)} kinds of request on silver.customers in the last hour:')
for r in rows:
    print(f'  {r.who}  {r.action_name:<24} {r.n}')
