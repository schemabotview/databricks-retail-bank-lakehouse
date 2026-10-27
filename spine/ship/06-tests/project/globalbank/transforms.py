"""Transforms as plain functions of DataFrames: testable on any Spark."""
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def velocity(auths: DataFrame, minutes: int = 10) -> DataFrame:
    """Each authorization, with how many its card made in the last minutes."""
    window = (Window.partitionBy('card_id')
              .orderBy(F.col('auth_ts').cast('long'))
              .rangeBetween(-minutes * 60, 0))
    return auths.withColumn('auths_10m', F.count('*').over(window))


def latest_change(changes: DataFrame, key: str) -> DataFrame:
    """The newest change per key, by the source's sequence, not by arrival."""
    newest = Window.partitionBy(key).orderBy(F.col('seq').desc())
    return (changes.withColumn('_n', F.row_number().over(newest))
            .where('_n = 1').drop('_n'))
