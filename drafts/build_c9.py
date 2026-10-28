"""Build spine/detect/* from spine/serve/07 (scratch builder, not part of the repo).

Labels exist only for September: the chargebacks for the 12 and 26 September card-testing rings.
So the rule is checked against them, the model trains on 12 September, is tested on 26 September,
and scores the unlabelled 22 October ring. The model is trained and scored ON THE LAPTOP (sklearn,
features pulled with Databricks Connect): Python UDFs over Connect fail on this Free Edition
workspace (ISOLATION_STARTUP_FAILURE.SANDBOX_STARTUP, checked 2026-10-27), so 9.7 scores each new
batch locally with the registered model, rather than inside a Spark stream. Tracking and the
registry are the workspace's (MLflow, Unity Catalog).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c5 import CAT, RESET, read, step  # noqa: E402

PARENT = 'serve/07-slow-query'
P = 'detect'

catalog_py = read(f'{PARENT}/project/globalbank/catalog.py').replace(
    "'landing.postings', ", "'landing.postings', 'landing.chargebacks',\n           ").replace(
    "'governance', 'vault']", "'governance', 'vault',\n          'ml']")
assert 'landing.chargebacks' in catalog_py and "'ml']" in catalog_py

REQUIREMENTS = """databricks-connect==18.3.7
mlflow-skinny[databricks]==3.17.2
scikit-learn==1.9.1
pandas==2.3.3
"""

BRONZE_ADD = """

@dp.table(name='globalbank_dev.bronze.chargebacks', table_properties=KEEP)
def chargebacks():
    return landed('chargebacks', 'csv', 'reported DATE')
"""

SILVER_ADD = """

@dp.materialized_view(name='globalbank_dev.silver.chargebacks')
def chargebacks():
    return spark.sql(\"\"\"
        SELECT DISTINCT auth_id, card_id, reported, reason
        FROM globalbank_dev.bronze.chargebacks\"\"\")
"""

RING = '''"""Card testing: many authorizations on one card in a few minutes, overnight."""
import sys

from globalbank.session import get_spark

day = sys.argv[1]
spark = get_spark()
cards = spark.sql(f"""
    SELECT card_id, count(*) AS auths, sum(amount) AS total,
           count_if(status = 'DECLINED') AS declined,
           count(DISTINCT merchant_id) AS merchants,
           min(auth_ts) AS first, max(auth_ts) AS last
    FROM globalbank_dev.silver.card_transactions
    WHERE to_date(auth_ts) = '{day}' AND hour(auth_ts) < 5
    GROUP BY card_id HAVING count(*) > 3 ORDER BY first""").collect()
print(f'{day}, before 05:00: {len(cards)} cards with more than 3 auths')
for c in cards:
    span = (c.last - c.first).seconds // 60
    print(f'  {c.card_id}  {c.auths} auths in {span:>2} min  {c.total:>6} EUR'
          f'  {c.declined} declined  {c.merchants} merchants')
one = cards[0].card_id
times = spark.sql(f"""
    SELECT auth_ts, amount FROM globalbank_dev.silver.card_transactions
    WHERE card_id = '{one}' AND to_date(auth_ts) = '{day}'
      AND hour(auth_ts) < 5 ORDER BY auth_ts""").collect()
print(f'{one}:', ' '.join(f"{t.auth_ts:%H:%M}/{t.amount}" for t in times))
'''

RULES_SQL = """-- Card testing, as a rule: more than 5 authorizations on one card within
-- 10 minutes. Illustrative threshold, not a real fraud policy.
WITH velocity AS (
  SELECT auth_id, card_id, auth_ts,
         count(*) OVER (PARTITION BY card_id ORDER BY auth_ts
                        RANGE BETWEEN INTERVAL 10 MINUTES PRECEDING
                                  AND CURRENT ROW) AS auths_10m
  FROM globalbank_dev.silver.card_transactions)
SELECT to_date(v.auth_ts) AS day,
       count_if(v.auths_10m > 5) AS flagged,
       count_if(v.auths_10m > 5 AND c.auth_id IS NOT NULL) AS fraud_flagged,
       count(c.auth_id) AS fraud
FROM velocity v
LEFT JOIN globalbank_dev.silver.chargebacks c USING (auth_id)
GROUP BY ALL ORDER BY day
"""

STREAM = '''"""The rule as a stream: 10-minute windows over bronze, flags into gold."""
from pyspark.sql import functions as F

from globalbank.session import get_spark

FLAGS = 'globalbank_dev.gold.fraud_flags'
CHECKPOINT = '/Volumes/globalbank_dev/bronze/checkpoints/fraud_flags'

spark = get_spark()
flags = (spark.readStream.table('globalbank_dev.bronze.card_auths')
         .withWatermark('auth_ts', '30 minutes')
         .groupBy(F.window('auth_ts', '10 minutes', '5 minutes'), 'card_id')
         .agg(F.count('*').alias('auths'), F.sum('amount').alias('total'))
         .where('auths > 5'))
query = (flags.writeStream.outputMode('append')
         .option('checkpointLocation', CHECKPOINT)
         .trigger(availableNow=True).toTable(FLAGS))
query.awaitTermination()
for f in spark.table(FLAGS).orderBy('window').collect():
    print(f"{f.window.start:%d %b %H:%M}-{f.window.end:%H:%M}  {f.card_id}"
          f"  {f.auths} auths  {f.total} EUR")
'''

FEATURES = '''"""Features per authorization, in Unity Catalog: what the model sees."""
from globalbank.session import get_spark

FEATURES = 'globalbank_dev.ml.card_features'

spark = get_spark()
spark.sql(f"""CREATE OR REPLACE TABLE {FEATURES} AS
    SELECT auth_id, card_id, auth_ts, to_date(auth_ts) AS day,
           count(*) OVER (PARTITION BY card_id ORDER BY auth_ts
                          RANGE BETWEEN INTERVAL 10 MINUTES PRECEDING
                                    AND CURRENT ROW) AS auths_10m,
           cast(entry_mode = 'online' AS INT) AS online,
           cast(amount < 2 AS INT) AS tiny_amount,
           cast(hour(auth_ts) < 5 AS INT) AS night,
           cast(auth_id IN (SELECT auth_id
                            FROM globalbank_dev.silver.chargebacks)
                AS INT) AS fraud
    FROM globalbank_dev.silver.card_transactions""")
print(f'{FEATURES}: {spark.table(FEATURES).count():,} rows')
spark.sql(f"""SELECT day, count(*) AS auths, sum(fraud) AS fraud,
                     round(avg(auths_10m), 2) AS avg_auths_10m
              FROM {FEATURES} GROUP BY day ORDER BY day""").show()
'''

TRAIN = '''"""Train on 12 September, test on 26 September, track the run in MLflow."""
import contextlib
import io
import logging
import os

os.environ['MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR'] = 'false'
import mlflow  # noqa: E402
from databricks.sdk import WorkspaceClient  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import precision_score, recall_score  # noqa: E402

from globalbank.session import get_spark  # noqa: E402

logging.getLogger('mlflow').setLevel(logging.ERROR)  # no run links
X = ['auths_10m', 'online', 'tiny_amount', 'night']
MODEL = 'globalbank_dev.ml.card_fraud'

spark = get_spark()
data = spark.table('globalbank_dev.ml.card_features').toPandas()
train = data[data.day.astype(str) == '2026-09-12']
test = data[data.day.astype(str) == '2026-09-26']
mlflow.set_tracking_uri('databricks')
mlflow.set_registry_uri('databricks-uc')
me = WorkspaceClient().current_user.me().user_name
quiet = io.StringIO()  # MLflow prints links and hints of its own
with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
    mlflow.set_experiment(f'/Users/{me}/globalbank_fraud')
    with mlflow.start_run(run_name='logreg-sep12') as run:
        model = LogisticRegression(C=1.0, class_weight='balanced')
        model.fit(train[X], train.fraud)
        seen = model.predict(test[X])
        metrics = {'precision': precision_score(test.fraud, seen),
                   'recall': recall_score(test.fraud, seen)}
        mlflow.log_params({'C': 1.0, 'features': ','.join(X),
                           'train_rows': len(train), 'test_rows': len(test)})
        mlflow.log_metrics(metrics)
        info = mlflow.sklearn.log_model(model, name='model',
                                        input_example=test[X].head(3),
                                        registered_model_name=MODEL)
print(f'trained on {len(train):,} rows ({int(train.fraud.sum())} fraud),'
      f' tested on {len(test):,} ({int(test.fraud.sum())} fraud)')
for name, value in metrics.items():
    print(f'  {name:<10}{value:.3f}')
print('  weights   ' + '  '.join(f'{x} {w:+.2f}'
                                  for x, w in zip(X, model.coef_[0])))
print(f'registered {MODEL} version {info.registered_model_version}')
'''

REGISTRY = '''"""The model in Unity Catalog: its versions, and which one is the champion."""
import sys

from mlflow import MlflowClient

MODEL = 'globalbank_dev.ml.card_fraud'

client = MlflowClient(tracking_uri='databricks', registry_uri='databricks-uc')
if len(sys.argv) > 2 and sys.argv[1] == 'champion':
    client.set_registered_model_alias(MODEL, 'champion', sys.argv[2])
model = client.get_registered_model(MODEL)
aliases = {a.version: a.alias for a in model.aliases}
print(f'{MODEL}:')
for v in client.search_model_versions(f"name = '{MODEL}'"):
    print(f'  version {v.version}  {v.status:<6} {aliases.get(v.version, "")}')
'''

SCORE = '''"""Score a day's authorizations with the champion model; flag what it finds."""
import logging
import os
import sys

os.environ['MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR'] = 'false'
import mlflow  # noqa: E402

from globalbank.session import get_spark  # noqa: E402

logging.getLogger('mlflow').setLevel(logging.ERROR)
X = ['auths_10m', 'online', 'tiny_amount', 'night']
FLAGS = 'globalbank_dev.gold.fraud_flags'

day, threshold = sys.argv[1], float(sys.argv[2])
spark = get_spark()
batch = spark.table('globalbank_dev.ml.card_features') \\
    .where(f"day = '{day}'").toPandas()
mlflow.set_tracking_uri('databricks')
mlflow.set_registry_uri('databricks-uc')
CHAMPION = 'models:/globalbank_dev.ml.card_fraud@champion'
model = mlflow.sklearn.load_model(CHAMPION)
batch['score'] = model.predict_proba(batch[X])[:, 1]
flagged = batch[batch.score >= threshold]
spark.createDataFrame(flagged[['auth_id', 'card_id', 'auth_ts', 'score']]) \\
    .write.mode('append').saveAsTable(FLAGS)
print(f'{day}: {len(batch):,} scored, {len(flagged)} flagged at {threshold}')
for card, rows in flagged.groupby('card_id'):
    print(f'  {card}  {len(rows)} auths  first {rows.auth_ts.min():%H:%M}'
          f'  score {rows.score.max():.2f}')
'''

TRADEOFF = '''"""Thresholds on 26 September: the analysts' queue against the fraud caught."""
import logging
import os

os.environ['MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR'] = 'false'
import mlflow  # noqa: E402

from globalbank.session import get_spark  # noqa: E402

logging.getLogger('mlflow').setLevel(logging.ERROR)
X = ['auths_10m', 'online', 'tiny_amount', 'night']

spark = get_spark()
test = spark.sql("""SELECT f.*, t.amount FROM globalbank_dev.ml.card_features f
                    JOIN globalbank_dev.silver.card_transactions t
                      USING (auth_id)
                    WHERE f.day = '2026-09-26'""").toPandas()
mlflow.set_tracking_uri('databricks')
mlflow.set_registry_uri('databricks-uc')
CHAMPION = 'models:/globalbank_dev.ml.card_fraud@champion'
model = mlflow.sklearn.load_model(CHAMPION)
test['score'] = model.predict_proba(test[X])[:, 1]
fraud = test[test.fraud == 1]
print(f'26 September: {len(test):,} authorizations, {len(fraud)} fraud,'
      f' {fraud.amount.sum()} EUR')
print('threshold  queue  caught  precision  recall  fraud EUR caught')
for t in (0.5, 0.7, 0.9, 0.97, 0.99):
    queue = test[test.score >= t]
    hit = queue[queue.fraud == 1]
    precision = len(hit) / max(len(queue), 1)
    print(f'{t:>9}  {len(queue):>5}  {len(hit):>6}  {precision:>9.2f}'
          f'  {len(hit) / len(fraud):>6.2f}  {hit.amount.sum():>16}')
'''

q = lambda c: c + ' > /dev/null'
DAYS = ['bash land.sh 2026-09-12 > /dev/null', 'bash land.sh 2026-09-26 > /dev/null',
        'bash land.sh 2026-10-22 > /dev/null']
SMALL = ['bash land.sh 2026-09-01 core_cdc 2026-09-02 > /dev/null', 'bash land.sh 2026-09-02 settlements > /dev/null',
         'bash land.sh 2026-09-01 postings > /dev/null', 'bash land.sh 2026-10-01 chargebacks > /dev/null']
PIPE = [q('python -m globalbank.deploy'), q('python -m globalbank.run')]
BASE = [RESET, CAT] + DAYS + SMALL + PIPE
GO = {'continues': True}  # from the workspace as the step before left it

PARENT_PIPES = {f'pipelines/{n}.py': read(f'{PARENT}/project/pipelines/{n}.py') for n in ('bronze', 'silver')}
if __name__ == '__main__':
    step(P, '01-card-testing', PARENT, ['globalbank/catalog.py', 'pipelines/bronze.py', 'pipelines/silver.py', 'globalbank/ring.py'],
         {'globalbank/catalog.py': catalog_py, 'pipelines/bronze.py': PARENT_PIPES['pipelines/bronze.py'] + BRONZE_ADD,
          'pipelines/silver.py': PARENT_PIPES['pipelines/silver.py'] + SILVER_ADD, 'globalbank/ring.py': RING},
         ['python -m globalbank.ring 2026-10-22'], BASE)
    step(P, '02-rules', f'{P}/01-card-testing', ['sql/fraud/velocity.sql'], {'sql/fraud/velocity.sql': RULES_SQL},
         ['python -m globalbank.warehouse sql/fraud/velocity.sql'], [], extra=GO)
    step(P, '03-streaming-rule', f'{P}/02-rules', ['globalbank/stream.py'], {'globalbank/stream.py': STREAM},
         ['python -m globalbank.stream'], [], extra=GO)
    step(P, '04-features', f'{P}/03-streaming-rule', ['globalbank/features.py'], {'globalbank/features.py': FEATURES},
         ['python -m globalbank.features'], [], extra=GO)
    step(P, '05-mlflow', f'{P}/04-features', ['requirements.txt', 'globalbank/train.py'],
         {'requirements.txt': REQUIREMENTS, 'globalbank/train.py': TRAIN},
         ['python -m globalbank.train'], [], extra={**GO, 'mask': [r'version \d+']})
    step(P, '06-registry', f'{P}/05-mlflow', ['globalbank/registry.py'], {'globalbank/registry.py': REGISTRY},
         ['python -m globalbank.registry', 'python -m globalbank.registry champion 1'],
         [], extra=GO)
    step(P, '07-score', f'{P}/06-registry', ['globalbank/score.py'], {'globalbank/score.py': SCORE},
         ['python -m globalbank.score 2026-10-22 0.9'], [], extra=GO)
    step(P, '08-tradeoff', f'{P}/07-score', ['globalbank/tradeoff.py'], {'globalbank/tradeoff.py': TRADEOFF},
         ['python -m globalbank.tradeoff'], [], extra=GO)
    print('built')
