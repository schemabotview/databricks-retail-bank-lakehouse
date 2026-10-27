"""Which tables each table was built from, as Unity Catalog recorded it."""
from globalbank.session import get_spark

spark = get_spark()
edges = spark.sql("""
    SELECT DISTINCT
           coalesce(source_table_full_name, 'files in ' || regexp_extract(
               source_path, '/Volumes/[^/]+/([^/]+/[^/]+)', 1)) AS source,
           target_table_full_name AS target
    FROM system.access.table_lineage
    WHERE target_table_catalog = 'globalbank_dev' AND source_type IS NOT NULL
      AND event_time > current_timestamp() - INTERVAL 2 HOURS
      AND target_table_full_name IN (SELECT table_catalog || '.' || table_schema
          || '.' || table_name FROM globalbank_dev.information_schema.tables)
    ORDER BY target, source""").collect()
for e in edges:
    print(f"{e.source.replace('globalbank_dev.', ''):<28} -> "
          f"{e.target.replace('globalbank_dev.', '')}")
