"""Publish the statements dashboard, then run each of its datasets once."""
import json
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import Dashboard

from globalbank.warehouse import run, show, warehouse

NAME = 'globalbank statements'

w = WorkspaceClient()
spec = Path('dashboards/statements.lvdash.json').read_text()
folder = f'/Workspace/Users/{w.current_user.me().user_name}/globalbank'
w.workspace.mkdirs(folder)
found = [d for d in w.lakeview.list() if d.display_name == NAME]
board = Dashboard(display_name=NAME, serialized_dashboard=spec,
                  warehouse_id=warehouse(w).id, parent_path=folder)
if found:
    w.lakeview.update(found[0].dashboard_id, dashboard=board)
else:
    found = [w.lakeview.create(board)]
w.lakeview.publish(found[0].dashboard_id, warehouse_id=warehouse(w).id)
print(f'{NAME}: published, {len(json.loads(spec)["datasets"])} datasets')
for dataset in json.loads(spec)['datasets']:
    print(f"-- {dataset['displayName']}")
    show(*run(w, ''.join(dataset['queryLines'])))
