"""This session's statements on the warehouse: what each one read."""
from databricks.sdk import WorkspaceClient

from globalbank.warehouse import run, show

w = WorkspaceClient()
show(*run(w, """
    SELECT left(regexp_replace(statement_text, '\\s+', ' '), 34) AS statement,
           read_files AS files, pruned_files AS pruned,
           round(read_bytes / 1e6, 1) AS read_mb
    FROM system.query.history
    WHERE start_time > current_timestamp() - INTERVAL 30 MINUTES
      AND executed_by = current_user() AND read_files > 0
      AND statement_text NOT LIKE '%system.query.history%'
    ORDER BY start_time DESC LIMIT 6"""))
