"""The last update, from the event log: each flow, its status, its duration."""
from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark

pipeline = next(WorkspaceClient().pipelines.list_pipelines(
    filter=f"name LIKE '{NAME}'"))
spark = get_spark()
log = f"event_log('{pipeline.pipeline_id}')"
spark.sql(f"""SELECT * FROM {log} WHERE origin.update_id = (
    SELECT origin.update_id FROM {log} WHERE event_type = 'create_update'
    ORDER BY timestamp DESC LIMIT 1)""").createOrReplaceTempView('last_update')
kinds = spark.sql("""SELECT event_type, count(*) AS n FROM last_update
                     GROUP BY ALL ORDER BY n DESC LIMIT 3""").collect()
print('events:', ', '.join(f'{k.event_type} {k.n}' for k in kinds))
for f in spark.sql("""
        SELECT origin.flow_name AS flow,
               max_by(details:flow_progress.status, timestamp) FILTER (
                   WHERE details:flow_progress.status IS NOT NULL) AS status,
               coalesce(timestampdiff(SECOND,
                   min(timestamp) FILTER (WHERE details:flow_progress.status
                                          = 'RUNNING'),
                   max(timestamp)), 0) AS secs
        FROM last_update WHERE event_type = 'flow_progress'
        GROUP BY ALL HAVING status IS NOT NULL ORDER BY flow""").collect():
    flow = f.flow.replace('globalbank_dev.', '')
    print(f'  {flow:<38}{f.status:<11}{f.secs:>4}s')
