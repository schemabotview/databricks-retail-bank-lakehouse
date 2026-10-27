"""Global Bank's catalog: a schema per medallion layer, and its volumes."""
from globalbank.session import get_spark

CATALOG = 'globalbank_dev'
LAYERS = ['landing', 'bronze', 'silver', 'gold', 'governance', 'vault']
VOLUMES = ['landing.card_auths', 'landing.settlements', 'landing.core_cdc',
           'bronze.checkpoints']


def create(spark):
    spark.sql(f'CREATE CATALOG IF NOT EXISTS {CATALOG}')
    for layer in LAYERS:
        spark.sql(f'CREATE SCHEMA IF NOT EXISTS {CATALOG}.{layer}')
    for volume in VOLUMES:
        spark.sql(f'CREATE VOLUME IF NOT EXISTS {CATALOG}.{volume}')


if __name__ == '__main__':
    spark = get_spark()
    create(spark)
    schemas = spark.sql(f'SHOW SCHEMAS IN {CATALOG}').collect()
    print('schemas:', ', '.join(r.databaseName for r in schemas))
    for v in VOLUMES:
        print('volume: ', f'/Volumes/{CATALOG}/' + v.replace('.', '/'))
