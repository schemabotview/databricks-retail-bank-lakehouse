"""What the core system sends: change records, counted, and one taken apart."""
import sys

from globalbank.session import get_spark

BRONZE = 'globalbank_dev.bronze.core_cdc'

spark = get_spark()
counts = spark.sql(f"""SELECT `table`, op, count(*) AS n FROM {BRONZE}
                       GROUP BY ALL ORDER BY ALL""").collect()
print('   '.join(f'{r.table} {r.op} {r.n:,}' for r in counts))
change = spark.table(BRONZE).where(f'seq = {sys.argv[1]}').first()
print('one change, as received:')
print(f'  op {change.op}   seq {change.seq}   table {change.table}'
      f'   ts {change.ts}')
print(f'  key    {change.key}')
lines = ['']
for part in change.after.split(','):  # wrap between fields, not inside one
    if len(lines[-1]) + len(part) > 68:
        lines.append('')
    lines[-1] += part + ','
print('  after  ' + '\n         '.join(lines).rstrip(','))
