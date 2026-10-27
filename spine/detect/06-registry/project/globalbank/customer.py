"""One customer: every change the core system sent, and silver's row now."""
import sys

from globalbank.session import get_spark

customer = sys.argv[1]
spark = get_spark()
changes = spark.sql(f"""
    SELECT regexp_extract(source_file, 'core_cdc/(.*).json', 1) AS file,
           seq, op, after:address AS address
    FROM globalbank_dev.bronze.core_cdc
    WHERE key:customer_id = '{customer}'
    ORDER BY source_file, seq""").collect()
print(f'{customer}, in the order the changes arrived:')
for c in changes:
    print(f'  {c.file}  seq {c.seq:>5}  {c.op}  {c.address}')
row = spark.table('globalbank_dev.silver.customers') \
    .where(f"customer_id = '{customer}'").first()
print(f'silver now: seq {row.seq}, {row.address}')
