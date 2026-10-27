"""A table's files: how many, how big. Small files make every read slower."""
import sys

from globalbank.session import get_spark

table = sys.argv[1]
spark = get_spark()
d = spark.sql(f'DESCRIBE DETAIL {table}').first()
print(f'{table}: {d.numFiles} files, {d.sizeInBytes / 1e6:.1f} MB,'
      f' {d.sizeInBytes / max(d.numFiles, 1) / 1e3:.0f} KB a file')
