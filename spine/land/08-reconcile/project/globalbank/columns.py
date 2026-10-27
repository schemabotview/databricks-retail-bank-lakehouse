"""Print a table's columns and their types, on one line."""
import sys

from globalbank.session import get_spark

table = sys.argv[1]
spark = get_spark()
print('  '.join(f'{n} {t}' for n, t in spark.table(table).dtypes))
