"""Global Bank's catalog: a schema per medallion layer, and a volume."""
from globalbank.session import get_spark

CATALOG = 'globalbank_dev'
LAYERS = ['landing', 'bronze', 'silver', 'gold']
VOLUMES = ['card_auths']  # one per source; Course 3 adds the rest


def create(spark):
    spark.sql(f'CREATE CATALOG IF NOT EXISTS {CATALOG}')
    for layer in LAYERS:
        spark.sql(f'CREATE SCHEMA IF NOT EXISTS {CATALOG}.{layer}')
    for volume in VOLUMES:
        spark.sql(f'CREATE VOLUME IF NOT EXISTS {CATALOG}.landing.{volume}')


if __name__ == '__main__':
    spark = get_spark()
    create(spark)
    schemas = spark.sql(f'SHOW SCHEMAS IN {CATALOG}').collect()
    print('schemas:', ', '.join(r.databaseName for r in schemas))
    for v in spark.sql(f'SHOW VOLUMES IN {CATALOG}.landing').collect():
        print('volume: ', f'/Volumes/{CATALOG}/{v.database}/{v.volume_name}')
