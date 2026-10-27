"""The nightly run's last check: did the day's clearing file arrive?"""
import sys

from databricks.sdk.runtime import dbutils
from pyspark.sql import SparkSession

day = sys.argv[1]
spark = SparkSession.builder.getOrCreate()
cleared = spark.sql(f"""SELECT count(*) FROM globalbank_dev.silver.settlements
                        WHERE cleared_date = '{day}'""").first()[0]
statements = spark.table('globalbank_dev.gold.monthly_statements').count()
print(f'{day}: {cleared} settlements cleared, {statements} statements')
if not cleared:
    raise SystemExit(f'no clearing file for {day}: the gold tables are stale')
dbutils.jobs.taskValues.set(key='cleared', value=cleared)
dbutils.jobs.taskValues.set(key='month', value=day[:7])
