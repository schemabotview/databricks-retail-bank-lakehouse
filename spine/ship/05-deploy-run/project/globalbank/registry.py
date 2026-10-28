"""The model in Unity Catalog: its versions, and which one is the champion."""
import sys

from mlflow import MlflowClient

MODEL = 'globalbank_dev.ml.card_fraud'

client = MlflowClient(tracking_uri='databricks', registry_uri='databricks-uc')
if len(sys.argv) > 2 and sys.argv[1] == 'champion':
    client.set_registered_model_alias(MODEL, 'champion', sys.argv[2])
model = client.get_registered_model(MODEL)
aliases = {str(v): a for a, v in model.aliases.items()}  # alias -> version
print(f'{MODEL}:')
for v in client.search_model_versions(f"name = '{MODEL}'"):
    print(f'  version {v.version}  {v.status:<6} {aliases.get(v.version, "")}')
