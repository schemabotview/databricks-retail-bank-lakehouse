"""Put globalbank_dev back to a known, empty state WITHOUT dropping the catalog, a schema or a volume.

A spine step's setup runs this first (through the step's own venv, which has the Databricks SDK):

    python "$SPINE_REPO/scripts/ws_reset.py"

Why not `databricks catalogs delete globalbank_dev --force`, as Course 2 first did: Unity Catalog
keeps a dropped managed volume for 7 days, and the metastore's volume QUOTA counts it for that long.
Free Edition's limit is 50 volumes per metastore; a few dozen replays that dropped and recreated the
catalog used all of it (2026-10-27: 9 live volumes, a quota count of 50), and no volume could be
created for a week. Dropped TABLES count against the table quota (500) the same way, so a replay
drops only the tables, and volumes are emptied, never dropped.

What it does: delete the course's own pipelines, jobs, dashboards and alerts (`globalbank` in the name,
Courses 7 on: a pipeline owns its tables, and Free Edition allows one pipeline per type); create
the catalog if missing; drop every table, view, function and registered model in the catalog's own
schemas; delete every file and folder inside every volume, keeping the volume.
"""
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

CATALOG = 'globalbank_dev'
KEEP = {'information_schema', 'default'}


def empty(w: WorkspaceClient, path: str) -> None:
    # A listing can still name an entry a moment after it is deleted (a replay once failed on one):
    # an entry already gone is what we wanted.
    for entry in list(w.files.list_directory_contents(path)):
        try:
            if entry.is_directory:
                empty(w, entry.path)
                w.files.delete_directory(entry.path)
            else:
                w.files.delete(entry.path)
        except NotFound:
            pass


def main() -> None:
    w = WorkspaceClient()
    for pipeline in w.pipelines.list_pipelines():
        if 'globalbank' in (pipeline.name or ''):
            try:
                w.pipelines.delete(pipeline.pipeline_id)
            except NotFound:  # the listing can still name one deleted a moment ago
                pass
    for job in w.jobs.list():
        if 'globalbank' in (job.settings.name or ''):
            try:
                w.jobs.delete(job.job_id)
            except NotFound:
                pass
    for dashboard in w.lakeview.list():
        if 'globalbank' in (dashboard.display_name or ''):
            w.lakeview.trash(dashboard.dashboard_id)
    for alert in w.alerts_v2.list_alerts():
        if 'globalbank' in (alert.display_name or ''):
            w.alerts_v2.trash_alert(alert.id)
    bundle = f'/Workspace/Users/{w.current_user.me().user_name}/.bundle/globalbank'
    try:  # a bundle's deployment state (Course 11): its resources are gone above
        w.workspace.delete(bundle, recursive=True)
    except NotFound:
        pass
    try:
        w.catalogs.get(CATALOG)
    except NotFound:
        # Through SQL, not the REST create: a metastore on Default Storage (the owner's second Free
        # Edition workspace, 2026-10-27) has no storage root, and the REST call refuses without a
        # location; serverless SQL puts the catalog on Default Storage by itself.
        from databricks.connect import DatabricksSession
        DatabricksSession.builder.serverless().getOrCreate().sql(f'CREATE CATALOG IF NOT EXISTS {CATALOG}')
    for schema in w.schemas.list(catalog_name=CATALOG):
        if schema.name in KEEP:
            continue
        for table in w.tables.list(catalog_name=CATALOG, schema_name=schema.name):
            try:
                w.tables.delete(table.full_name)
            except NotFound:  # a deleted pipeline's tables go with it
                pass
        for function in w.functions.list(catalog_name=CATALOG, schema_name=schema.name):
            w.functions.delete(function.full_name)
        for model in w.registered_models.list(catalog_name=CATALOG, schema_name=schema.name):
            w.registered_models.delete(model.full_name)  # Course 9's, with its versions
        for volume in w.volumes.list(catalog_name=CATALOG, schema_name=schema.name):
            empty(w, f'/Volumes/{CATALOG}/{schema.name}/{volume.name}')


if __name__ == '__main__':
    main()
