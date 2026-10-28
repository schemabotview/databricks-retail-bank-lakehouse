"""This session's statements on the warehouse: what each one read."""
import time

from databricks.sdk import WorkspaceClient

from globalbank.warehouse import run, show

RECENT = """start_time > current_timestamp() - INTERVAL 30 MINUTES
    AND executed_by = current_user() AND compute.type = 'WAREHOUSE'"""
w = WorkspaceClient()
for _ in range(40):  # the history arrives some minutes after a statement
    _, found = run(w, f"""SELECT count(*) FROM system.query.history
        WHERE {RECENT} AND statement_text LIKE '%cleared_date = DATE%'
          AND statement_text NOT LIKE '%system.query%'""")
    if int(found[0][0]):
        break
    time.sleep(30)
show(*run(w, rf"""
    SELECT left(regexp_replace(statement_text, '\\s+', ' '), 34) AS statement,
           read_files AS files, pruned_files AS pruned,
           round(read_bytes / 1e6, 1) AS read_mb
    FROM system.query.history
    WHERE {RECENT} AND read_files > 0
      AND statement_text NOT LIKE '%system.query%'
    ORDER BY start_time DESC LIMIT 6"""))
