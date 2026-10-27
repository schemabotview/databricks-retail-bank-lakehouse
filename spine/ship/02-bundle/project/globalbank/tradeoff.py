"""Thresholds on 26 September: the analysts' queue against the fraud caught."""
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
