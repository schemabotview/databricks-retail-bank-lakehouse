"""Run globalbank_pipeline once and wait: what each dataset holds after it."""
import sys
import time

from databricks.sdk import WorkspaceClient

from globalbank.deploy import NAME
from globalbank.session import get_spark



def start(w, pipeline_id, **kwargs):
    for _ in range(12):  # a pipeline created a moment ago may not be found yet
        try:
            return w.pipelines.start_update(pipeline_id, **kwargs).update_id
        except Exception:
            time.sleep(10)
    raise SystemExit('the pipeline never became ready')


if __name__ == '__main__':
    w = WorkspaceClient()
    pipeline = next(w.pipelines.list_pipelines(filter=f"name LIKE '{NAME}'"))
    update = start(w, pipeline.pipeline_id,
                   full_refresh='--full-refresh' in sys.argv)
    while (state := w.pipelines.get_update(pipeline.pipeline_id, update)
           .update.state.value) not in ('COMPLETED', 'FAILED', 'CANCELED'):
        time.sleep(10)
    print(f'update {state}')
    if state != 'COMPLETED':
        errors = [e.message for e in w.pipelines.list_pipeline_events(
            pipeline.pipeline_id,
            filter=f"level='ERROR' AND update_id='{update}'")]
        raise SystemExit('\n'.join(m[:78] for m in errors[-2:]))
    spark = get_spark()
    events = spark.sql(f"""SELECT * FROM event_log('{pipeline.pipeline_id}')
                           WHERE origin.update_id = '{update}'""")
    datasets = events.where("event_type = 'flow_definition'").selectExpr(
        'details:flow_definition.output_dataset AS name').distinct().collect()
    planned = events.where("event_type = 'planning_information'")
    chosen = """filter(from_json(
        details:planning_information.technique_information,
        'ARRAY<STRUCT<maintenance_type STRING, is_chosen BOOLEAN>>'),
        x -> x.is_chosen)[0].maintenance_type"""
    plans = {r.f: r.t for r in planned.selectExpr(
        'origin.flow_name AS f', f'{chosen} AS t').collect()}
    for d in sorted(r.name for r in datasets if r.name.count('.') == 2):
        rows = spark.table(d).count()
        how = (plans.get(d) or '').removeprefix('MAINTENANCE_TYPE_').lower()
        how = f'  ({how})' if how else ''  # how a materialized view refreshed
        print(f"  {d.replace('globalbank_dev.', ''):<36}{rows:>9,} rows{how}")
