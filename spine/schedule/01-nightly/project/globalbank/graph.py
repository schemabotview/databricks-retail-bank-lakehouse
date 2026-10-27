"""The pipeline's graph, as its last update declared it: what reads what."""
from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark

pipeline = next(WorkspaceClient().pipelines.list_pipelines(
    filter=f"name LIKE '{NAME}'"))
edges = get_spark().sql(f"""
    SELECT details:flow_definition.output_dataset AS target,
           explode(from_json(details:flow_definition.input_datasets,
                             'ARRAY<STRING>')) AS source
    FROM event_log('{pipeline.pipeline_id}')
    WHERE event_type = 'flow_definition' AND origin.update_id = (
        SELECT origin.update_id FROM event_log('{pipeline.pipeline_id}')
        WHERE event_type = 'create_update' ORDER BY timestamp DESC LIMIT 1)
    ORDER BY target, source""").collect()
short = lambda name: name.replace('globalbank_dev.', '')
for e in edges:
    print(f'{short(e.source):<26} -> {short(e.target)}')
