"""Score a day's authorizations with the champion model; flag what it finds."""
import logging
import os
import sys

os.environ['MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR'] = 'false'
import mlflow  # noqa: E402

from globalbank.session import get_spark  # noqa: E402

logging.getLogger('mlflow').setLevel(logging.ERROR)
X = ['auths_10m', 'online', 'tiny_amount', 'night']
# The model's scores. gold.fraud_flags is the rule's (the stream, the job).
SCORES = 'globalbank_dev.ml.fraud_scores'

day, threshold = sys.argv[1], float(sys.argv[2])
spark = get_spark()
batch = spark.table('globalbank_dev.ml.card_features') \
    .where(f"day = '{day}'").toPandas()
mlflow.set_tracking_uri('databricks')
mlflow.set_registry_uri('databricks-uc')
CHAMPION = 'models:/globalbank_dev.ml.card_fraud@champion'
model = mlflow.sklearn.load_model(CHAMPION)
batch['score'] = model.predict_proba(batch[X])[:, 1]
flagged = batch[batch.score >= threshold]
spark.createDataFrame(flagged[['auth_id', 'card_id', 'auth_ts', 'score']]) \
    .write.mode('append').saveAsTable(SCORES)
print(f'{day}: {len(batch):,} scored, {len(flagged)} flagged at {threshold}')
for card, rows in flagged.groupby('card_id'):
    print(f'  {card}  {len(rows)} auths  first {rows.auth_ts.min():%H:%M}'
          f'  score {rows.score.max():.2f}')
