"""Put globalbank_dev back to a known, empty state WITHOUT dropping the catalog, a schema or a volume.

A spine step's setup runs this first (through the step's own venv, which has the Databricks SDK):

    python "$SPINE_REPO/scripts/ws_reset.py"

Why not `databricks catalogs delete globalbank_dev --force`, as Course 2 first did: Unity Catalog
keeps a dropped managed volume for 7 days, and the metastore's volume QUOTA counts it for that long.
Free Edition's limit is 50 volumes per metastore; a few dozen replays that dropped and recreated the
catalog used all of it (2026-10-27: 9 live volumes, a quota count of 50), and no volume could be
created for a week. Dropped TABLES count against the table quota (500) the same way, so a replay
drops only the tables, and volumes are emptied, never dropped.

What it does: create the catalog and the layer schemas if missing; drop every table and view in the
catalog's own schemas; delete every file and folder inside every volume, keeping the volume.
"""
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

CATALOG = 'globalbank_dev'
KEEP = {'information_schema', 'default'}


def empty(w: WorkspaceClient, path: str) -> None:
    for entry in w.files.list_directory_contents(path):
        if entry.is_directory:
            empty(w, entry.path)
            w.files.delete_directory(entry.path)
        else:
            w.files.delete(entry.path)


def main() -> None:
    w = WorkspaceClient()
    try:
        w.catalogs.get(CATALOG)
    except NotFound:
        w.catalogs.create(CATALOG)
    for schema in w.schemas.list(catalog_name=CATALOG):
        if schema.name in KEEP:
            continue
        for table in w.tables.list(catalog_name=CATALOG, schema_name=schema.name):
            w.tables.delete(table.full_name)
        for volume in w.volumes.list(catalog_name=CATALOG, schema_name=schema.name):
            empty(w, f'/Volumes/{CATALOG}/{schema.name}/{volume.name}')


if __name__ == '__main__':
    main()
