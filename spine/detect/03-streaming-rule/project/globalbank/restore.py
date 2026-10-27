"""Put a table back to an earlier version. The restore is a version too."""
import sys

from globalbank.session import get_spark

table, version = sys.argv[1], sys.argv[2]
spark = get_spark()
result = spark.sql(f'RESTORE TABLE {table} TO VERSION AS OF {version}')
r = result.first()
print(f'{table}: removed {r.num_removed_files} file(s),'
      f' restored {r.num_restored_files}')
