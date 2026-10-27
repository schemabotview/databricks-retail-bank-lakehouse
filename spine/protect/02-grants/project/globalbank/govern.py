"""Apply a governance file: each statement, and what the workspace said."""
import re
import sys

from globalbank.session import get_spark

spark = get_spark()
done = refused = 0
reasons = set()
for statement in open(sys.argv[1]).read().split(';\n'):  # at line ends
    sql = '\n'.join(line for line in statement.splitlines()
                    if not line.lstrip().startswith('--')).strip()
    if not sql:
        continue
    shown = ' '.join(sql.split()).replace('globalbank_dev.', '')[:66]
    try:
        spark.sql(sql)
        done += 1
        print(f'ok   {shown}')
    except Exception as e:
        refused += 1
        reason = re.search(r'ErrorClass=([A-Z_]+)|\[([A-Z_]{4,})[.\]]', str(e))
        reasons.add(next(filter(None, reason.groups())) if reason
                    else type(e).__name__)
        print(f'no   {shown}')
print(f'{done} applied, {refused} refused' +
      (f': {", ".join(sorted(reasons))}' if reasons else ''))
