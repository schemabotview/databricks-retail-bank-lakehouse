"""Every column tagged pii in the catalog: what it holds, and where."""
from globalbank.session import get_spark

spark = get_spark()
tagged = spark.sql("""
    SELECT schema_name, table_name, column_name, tag_value
    FROM globalbank_dev.information_schema.column_tags
    WHERE tag_name = 'pii' ORDER BY ALL""").collect()
print(f'{len(tagged)} columns tagged pii in globalbank_dev:')
for t in tagged:
    name = f'{t.schema_name}.{t.table_name}.{t.column_name}'
    print(f'  {name:<32}{t.tag_value}')
