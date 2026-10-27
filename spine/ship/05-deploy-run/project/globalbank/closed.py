"""Closed accounts: gone from silver, still in bronze's change records."""
from globalbank.session import get_spark

spark = get_spark()
closed = spark.sql("""
    SELECT b.key:account_id AS account_id, b.seq,
           regexp_extract(b.source_file, 'core_cdc/(.*)', 1) AS file,
           s.account_id IS NOT NULL AS in_silver
    FROM globalbank_dev.bronze.core_cdc b
    LEFT JOIN globalbank_dev.silver.accounts s
      ON s.account_id = b.key:account_id
    WHERE b.`table` = 'accounts' AND b.op = 'D'""")
print(f'{closed.count()} D records in bronze;'
      f' {closed.where("in_silver").count()} of their accounts in silver')
for c in closed.orderBy('seq').limit(3).collect():
    print(f"  {c.account_id}  seq {c.seq}  {c.file}"
          f"  in silver: {'yes' if c.in_silver else 'no'}")
