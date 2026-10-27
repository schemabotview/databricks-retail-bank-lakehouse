"""Run a .sql file on the workspace's SQL warehouse, from the laptop."""
import sys
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (StatementParameterListItem,
                                       StatementState)


def warehouse(w):
    return next(w.warehouses.list())  # Free Edition has one


def run(w, sql, **params):
    r = w.statement_execution.execute_statement(
        warehouse_id=warehouse(w).id, statement=sql, wait_timeout='30s',
        parameters=[StatementParameterListItem(name=k, value=str(v))
                    for k, v in params.items()])
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        raise SystemExit(f'{r.status.state.value}: {r.status.error.message}')
    columns = [c.name for c in r.manifest.schema.columns]
    return columns, (r.result.data_array or []) if r.result else []


def show(columns, rows):
    """Print a result as aligned columns: numbers right, text left."""
    cols = list(zip(*rows)) if rows else [()] * len(columns)
    widths = [max([len(c)] + [len(str(v)) for v in col])
              for c, col in zip(columns, cols)]
    number = lambda v: str(v)[:1].isdigit() or str(v)[:1] == '-'
    for line in [columns] + rows:
        print('  '.join(str(v).rjust(n) if number(v) else str(v).ljust(n)
                        for v, n in zip(line, widths)).rstrip())


if __name__ == '__main__':
    w = WorkspaceClient()
    if sys.argv[1] == '--about':
        wh = warehouse(w)
        print(f'{wh.name}: {wh.cluster_size},'
              f' serverless {wh.enable_serverless_compute}')
        raise SystemExit
    path = Path(sys.argv[1])
    params = dict(arg.split('=', 1) for arg in sys.argv[2:])
    for sql in [s for s in path.read_text().split(';') if s.strip()]:
        columns, rows = run(w, sql, **params)
        if rows:  # a CREATE … AS returns nothing to show
            show(columns, rows)
