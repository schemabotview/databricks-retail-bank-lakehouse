"""Unity Catalog's names, from the top: catalog, schemas, what each holds."""
from globalbank.session import get_spark

spark = get_spark()
print('metastore:', spark.sql('SELECT current_metastore()').first()[0])
catalogs = spark.sql("SHOW CATALOGS LIKE 'globalbank*'").collect()
print('catalogs: ', ', '.join(r.catalog for r in catalogs))
print('owner:    ', spark.sql("""SELECT catalog_owner
    FROM system.information_schema.catalogs
    WHERE catalog_name = 'globalbank_dev'""").first()[0])
print('globalbank_dev:')
for schema in ['landing', 'bronze', 'silver', 'gold', 'governance', 'vault']:
    tables = spark.sql(f'SHOW TABLES IN globalbank_dev.{schema}').count()
    volumes = spark.sql(f'SHOW VOLUMES IN globalbank_dev.{schema}').count()
    print(f'  {schema:<11} {tables} tables, {volumes} volumes')
