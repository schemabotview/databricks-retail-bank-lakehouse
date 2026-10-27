"""Honour an erasure request: delete the customer from the vault."""
import csv
import glob

from globalbank.session import get_spark

VAULT = 'globalbank_dev.vault.customer_pii'

path = glob.glob('landing/privacy/erasure-requests-*.csv')[0]
request = next(csv.DictReader(open(path)))
customer = request['customer_id']
print(f"request {request['request_id']}: erase {customer}")
spark = get_spark()
spark.sql(f"DELETE FROM {VAULT} WHERE customer_id = '{customer}'")
last = spark.sql(f'DESCRIBE HISTORY {VAULT} LIMIT 1').first()
m = last.operationMetrics
print(f"version {last.version}: deleted {m['numDeletedRows']} row(s),"
      f" deletion vectors added {m.get('numDeletionVectorsAdded', 0)}")
for v in (last.version - 1, last.version):
    n = spark.sql(f"""SELECT count(*) FROM {VAULT} VERSION AS OF {v}
                      WHERE customer_id = '{customer}'""").first()[0]
    print(f'  version {v} holds them: {n} row(s)')
facts = spark.sql(f"""SELECT count(*) FROM globalbank_dev.silver.accounts
                      WHERE customer_id = '{customer}'""").first()[0]
print(f'silver.accounts still holds {facts} account row(s) for {customer}')
