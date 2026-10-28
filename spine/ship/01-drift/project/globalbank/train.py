"""Train on 12 September, test on 26 September, track the run in MLflow."""
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
