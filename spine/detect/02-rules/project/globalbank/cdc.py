"""Silver customers and accounts from the core system's changes (SCD type 1)."""
import sys

from globalbank.session import get_spark

BRONZE = 'globalbank_dev.bronze.core_cdc'
TABLES = {  # table: (key, columns)
    'customers': ('customer_id',
                  'customer_id STRING, first_name STRING, last_name STRING,'
                  ' national_id STRING, date_of_birth DATE, email STRING,'
                  ' address STRING, region STRING, branch_id STRING,'
                  ' segment STRING, kyc_status STRING, customer_since DATE'),
    'accounts': ('account_id',
                 'account_id STRING, customer_id STRING, product STRING,'
                 ' iban STRING, opened DATE, status STRING,'
                 ' overdraft_limit DECIMAL(18,2),'
                 ' opening_balance DECIMAL(18,2)'),
}


def apply(spark, table, files):
    """Apply a batch of change files to silver: the latest change per key."""
    key, schema = TABLES[table]
    silver = f'globalbank_dev.silver.{table}'
    spark.sql(f'CREATE TABLE IF NOT EXISTS {silver} ({schema}, seq BIGINT)')
    cols = [c.split()[0] for c in schema.split(', ')]
    batch = spark.sql(f"""
        SELECT op, seq, get_json_object(key, '$.{key}') AS k,
               from_json(after, '{schema}') AS a
        FROM {BRONZE}
        WHERE `table` = '{table}' AND source_file RLIKE '{files}'
        QUALIFY row_number() OVER (PARTITION BY k ORDER BY seq DESC) = 1""")
    batch.createOrReplaceTempView('batch')
    spark.sql(f"""MERGE INTO {silver} t USING batch s ON t.{key} = s.k
        WHEN MATCHED AND s.seq > t.seq AND s.op = 'D' THEN DELETE
        WHEN MATCHED AND s.seq > t.seq THEN UPDATE SET
            {', '.join(f't.{c} = s.a.{c}' for c in cols)}, t.seq = s.seq
        WHEN NOT MATCHED AND s.op != 'D' THEN INSERT ({', '.join(cols)}, seq)
            VALUES ({', '.join(f's.a.{c}' for c in cols)}, s.seq)""")
    return batch.count()


if __name__ == '__main__':
    spark = get_spark()
    table, files = sys.argv[1], sys.argv[2]
    n = apply(spark, table, files)
    silver = f'globalbank_dev.silver.{table}'
    m = spark.sql(f'DESCRIBE HISTORY {silver} LIMIT 1').first().operationMetrics
    print(f'{table} <- {files}: {n:,} changes')
    print(f"  inserted {m['numTargetRowsInserted']},"
          f" updated {m['numTargetRowsUpdated']},"
          f" deleted {m['numTargetRowsDeleted']};"
          f" silver.{table}: {spark.table(silver).count():,} rows")
