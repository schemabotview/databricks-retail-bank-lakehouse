"""Compact a table's small files into fewer, bigger ones."""
import sys

from globalbank.session import get_spark

table = sys.argv[1]
m = get_spark().sql(f'OPTIMIZE {table}').first().metrics
print(f'OPTIMIZE {table}: {m.numFilesRemoved} files removed,'
      f' {m.numFilesAdded} added')
