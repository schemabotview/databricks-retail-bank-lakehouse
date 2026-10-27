"""Predictive optimization: is it on here, and what has it run on our tables?"""
from globalbank.session import get_spark

spark = get_spark()
info = spark.sql('DESCRIBE SCHEMA EXTENDED globalbank_dev.silver').collect()
for r in info:
    if 'Predictive' in r[0]:
        print(f'{r[0]}: {r[1]}')
ops = spark.sql("""
    SELECT operation_type, count(*) AS n
    FROM system.storage.predictive_optimization_operations_history
    WHERE catalog_name = 'globalbank_dev' GROUP BY ALL""").collect()
print(f'operations on globalbank_dev so far: {len(ops)} kinds')
for o in ops:
    print(f'  {o.operation_type:<12}{o.n}')
history = spark.sql('DESCRIBE HISTORY globalbank_dev.silver.auths_clustered')
print('silver.auths_clustered, by operation:',
      ', '.join(f'{r.operation} {r.n}' for r in history.groupBy('operation')
                .count().withColumnRenamed('count', 'n').collect()))
