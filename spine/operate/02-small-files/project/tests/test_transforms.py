"""Unit tests: local PySpark, no workspace, a few seconds."""
import os
import sys
from datetime import datetime, timedelta

import pytest
from pyspark.sql import SparkSession

from globalbank.transforms import latest_change, velocity


@pytest.fixture(scope='session')
def spark():
    os.environ['PYSPARK_PYTHON'] = sys.executable  # workers: this Python too
    return SparkSession.builder.master('local[1]').getOrCreate()


def test_velocity_counts_ten_minutes(spark):
    t = datetime(2026, 10, 22, 2, 10)
    rows = [('K1', t + timedelta(minutes=m)) for m in (0, 1, 2, 3, 4, 5, 30)]
    schema = 'card_id STRING, auth_ts TIMESTAMP'
    out = velocity(spark.createDataFrame(rows, schema))
    assert [r.auths_10m for r in out.orderBy('auth_ts').collect()] == \
        [1, 2, 3, 4, 5, 6, 1]


def test_latest_change_wins_by_sequence(spark):
    arrived = [('C1', 12155, '136 River View'), ('C1', 12148, '6 River View')]
    schema = 'customer_id STRING, seq BIGINT, address STRING'
    out = latest_change(spark.createDataFrame(arrived, schema), 'customer_id')
    assert out.first().address == '136 River View'
