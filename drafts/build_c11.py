"""Build spine/ship/* from spine/schedule/07 (scratch builder, not part of the repo).

A Declarative Automation Bundle deploys the pipeline, the nightly job and the dashboard from the
repo (databricks.yml + resources/*.yml; the job's YAML is Course 10's file, unchanged). The dev
target sets its own name prefix, so no name derived from the user's email is shown. Free Edition
has one workspace and one pipeline per type, so the prod target is validated, not deployed: a real
bank's prod is another workspace. Tests: transforms unit-tested with LOCAL PySpark (run local, a
venv of its own: PySpark and Databricks Connect cannot share one) and one Connect test on the
workspace. CI is documented.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c5 import CAT, RESET, read, step  # noqa: E402

PARENT = 'schedule/07-run-as'
P = 'ship'

DRIFT = '''"""Has the deployed job drifted from resources/nightly.yml? Someone clicks."""
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import JobSettings

from globalbank.job import NAME, job_id, settings

w = WorkspaceClient()
# What a person did in the web UI, done here as the API call the UI makes:
edited = w.jobs.get(job_id(w)).settings
edited.max_concurrent_runs = 3
edited.tags = {'edited': 'by hand'}
w.jobs.reset(job_id(w), new_settings=edited)
print(f'{NAME}, edited in the workspace')

code = settings(w).as_dict()
live = w.jobs.get(job_id(w)).settings.as_dict()
for key in sorted(set(code) | set(live)):
    if key in ('tasks', 'environments') or code.get(key) == live.get(key):
        continue
    print(f'  {key:<20} repo: {code.get(key, "-")!s:<10}'
          f' workspace: {live.get(key)}')
'''

BUNDLE = """# Global Bank's lakehouse, as one bundle: the code, the pipeline, the nightly
# job and the dashboard, deployed together from the repo.
bundle:
  name: globalbank

include:
  - resources/*.yml

sync:
  exclude: [.venv, .venv-test, landing]

variables:
  warehouse_id:
    lookup: {warehouse: Serverless Starter Warehouse}

targets:
  dev:
    mode: development  # schedules and triggers paused
    default: true
    presets: {name_prefix: dev_}
#PROD#"""

PROD = """  prod:
    mode: production
    workspace:
      root_path: /Workspace/Shared/.bundle/${bundle.name}/prod
"""

PIPELINE_YML = """# The medallion pipeline (Course 7), deployed by the bundle.
resources:
  pipelines:
    globalbank_pipeline:
      name: globalbank_pipeline
      serverless: true
      catalog: globalbank_dev
      schema: bronze
      libraries:
        - file: {path: ../pipelines/bronze.py}
        - file: {path: ../pipelines/silver.py}
        - file: {path: ../pipelines/gold.py}
"""

DASHBOARD_YML = """# The statements dashboard (Course 8), deployed by the bundle.
resources:
  dashboards:
    globalbank_statements:
      display_name: globalbank statements
      file_path: ../dashboards/statements.lvdash.json
      warehouse_id: ${var.warehouse_id}
"""

TRANSFORMS = '''"""Transforms as plain functions of DataFrames: testable on any Spark."""
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
'''

TEST_LOCAL = '''"""Unit tests: local PySpark, no workspace, a few seconds."""
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
    assert [r.auths_10m for r in out.orderBy('auth_ts').collect()] == \\
        [1, 2, 3, 4, 5, 6, 1]


def test_latest_change_wins_by_sequence(spark):
    arrived = [('C1', 12155, '136 River View'), ('C1', 12148, '6 River View')]
    schema = 'customer_id STRING, seq BIGINT, address STRING'
    out = latest_change(spark.createDataFrame(arrived, schema), 'customer_id')
    assert out.first().address == '136 River View'
'''

TEST_WS = '''"""One integration test: the same transform, on the workspace's real silver."""
from globalbank.session import get_spark
from globalbank.transforms import velocity


def test_velocity_finds_the_october_ring():
    auths = get_spark().table('globalbank_dev.silver.card_transactions') \\
        .where("to_date(auth_ts) = '2026-10-22'")
    flagged = velocity(auths).where('auths_10m > 5')
    cards = {r.card_id for r in flagged.select('card_id').distinct().collect()}
    assert len(cards) == 6  # the 22 October ring: six cards
'''

REQUIREMENTS = read(f'{PARENT}/project/requirements.txt') + 'pytest==8.4.2\n'

WORKFLOW = """# CI/CD: test every pull request; deploy prod from main.
name: deploy
on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install pyspark==4.2.0 pytest==8.4.2
      - run: pytest -q tests/test_transforms.py

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    env:  # a service principal's OAuth secret, stored in GitHub
      DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST }}
      DATABRICKS_CLIENT_ID: ${{ vars.DATABRICKS_CLIENT_ID }}
      DATABRICKS_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
    steps:
      - uses: actions/checkout@v4
      - uses: databricks/setup-cli@main
      - run: databricks bundle deploy -t prod
"""

q = lambda c: c + ' > /dev/null'
LAND = [RESET, CAT, 'bash land.sh 2026-10-22 > /dev/null', 'bash land.sh 2026-09-01 core_cdc 2026-10-31 > /dev/null',
        'bash land.sh 2026-09-01 postings 2026-10-31 > /dev/null', 'bash land.sh 2026-10-01 chargebacks > /dev/null',
        'bash land.sh 2026-09-02 settlements 2026-10-31 > /dev/null']
B = 'databricks bundle'
TESTENV = ['python -m venv .venv-test', '.venv-test/bin/pip install -q pyspark==4.2.0 pytest==8.4.2']

if __name__ == '__main__':
    step(P, '01-drift', PARENT, ['globalbank/drift.py'], {'globalbank/drift.py': DRIFT},
         ['python -m globalbank.drift'], LAND + [q('python -m globalbank.deploy'), q('python -m globalbank.job deploy')])
    step(P, '02-bundle', f'{P}/01-drift', ['databricks.yml', 'resources/globalbank_pipeline.yml'],
         {'databricks.yml': BUNDLE.replace('#PROD#', ''), 'resources/globalbank_pipeline.yml': PIPELINE_YML},
         [f'{B} validate'], [RESET])
    step(P, '03-resources', f'{P}/02-bundle', ['resources/dashboard.yml'], {'resources/dashboard.yml': DASHBOARD_YML},
         [f'{B} summary'], [RESET])
    step(P, '04-targets', f'{P}/03-resources', ['databricks.yml'], {'databricks.yml': BUNDLE.replace('#PROD#', PROD)},
         [f'{B} validate -t dev | sed -n 1,5p', f'{B} validate -t prod | sed -n 1,5p'], [RESET])
    step(P, '05-deploy-run', f'{P}/04-targets', ['globalbank/drift.py'], {'globalbank/drift.py': None},
         [f'{B} deploy', f'{B} run globalbank_nightly | tail -1'], LAND,
         extra={'volatile': ['ts'], 'mask': [r'Files: \d+ uploaded']})
    step(P, '06-tests', f'{P}/05-deploy-run', ['requirements.txt', 'globalbank/transforms.py', 'tests/test_transforms.py',
                                               'tests/test_workspace.py'],
         {'requirements.txt': REQUIREMENTS, 'globalbank/transforms.py': TRANSFORMS,
          'tests/test_transforms.py': TEST_LOCAL, 'tests/test_workspace.py': TEST_WS},
         ['.venv-test/bin/python -m pytest -q tests/test_transforms.py 2>&1 | tail -1',
          'python -m pytest -q tests/test_workspace.py 2>&1 | tail -1'],
         LAND[:3] + [q(f'{B} deploy'), q(f'{B} run globalbank_pipeline')] + TESTENV,
         extra={'mask': [r'in [\d.]+s']})
    step(P, '07-ci', f'{P}/06-tests', ['.github/workflows/deploy.yml'], {'.github/workflows/deploy.yml': WORKFLOW},
         [f'{B} validate -t prod | tail -1'], [RESET])
    print('built')
