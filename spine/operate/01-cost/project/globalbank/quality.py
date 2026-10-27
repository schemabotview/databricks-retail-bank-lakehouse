"""What each expectation passed and failed in the last update."""
from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark

pipeline = next(WorkspaceClient().pipelines.list_pipelines(
    filter=f"name LIKE '{NAME}'"))
rows = get_spark().sql(f"""
    SELECT e.name, e.passed_records AS passed, e.failed_records AS failed
    FROM (SELECT explode(from_json(
              details:flow_progress.data_quality.expectations,
              'ARRAY<STRUCT<name STRING, passed_records BIGINT,
                            failed_records BIGINT>>')) AS e
          FROM event_log('{pipeline.pipeline_id}')
          WHERE event_type = 'flow_progress' AND origin.update_id = (
              SELECT origin.update_id FROM event_log('{pipeline.pipeline_id}')
              WHERE event_type = 'create_update'
              ORDER BY timestamp DESC LIMIT 1))
    ORDER BY e.name""").collect()
for r in rows:
    print(f'{r.name:<18} passed {r.passed:>7,}   failed {r.failed:>4,}')
