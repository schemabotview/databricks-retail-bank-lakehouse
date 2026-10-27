"""Make an erasure physical: rewrite the files, then remove the old ones."""
from globalbank.session import get_spark

VAULT = 'globalbank_dev.vault.customer_pii'

spark = get_spark()
spark.sql(f'REORG TABLE {VAULT} APPLY (PURGE)')
m = spark.sql(f'DESCRIBE HISTORY {VAULT} LIMIT 1').first().operationMetrics
print(f"REORG ... PURGE: {m['numAddedFiles']} file written,"
      f" {m['numRemovedFiles']} removed from the table")
spark.sql(f'VACUUM {VAULT}')
start = spark.sql(f"DESCRIBE HISTORY {VAULT}").where(
    "operation = 'VACUUM START'").first().operationMetrics
print(f"VACUUM: {start['numFilesToDelete']} files deleted now;"
      ' the old file goes after the 7-day retention')
