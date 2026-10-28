"""The regulator's question: the report as it stood then, and as it is now."""
from databricks.sdk import WorkspaceClient

from globalbank.warehouse import run, show

SNAPSHOT = 'globalbank_dev.gold.regulatory_snapshot'

w = WorkspaceClient()
_, history = run(w, f'DESCRIBE HISTORY {SNAPSHOT}')
first, last = history[-1], history[0]  # newest first
print(f'as reported: version {first[0]}    as restated: version {last[0]}')
show(*run(w, f"""
    SELECT day, reported.approved, reported.cleared AS cleared_then,
           coalesce(reported.cleared_eur, 0) AS eur_then,
           restated.cleared AS cleared_now, restated.cleared_eur AS eur_now
    FROM {SNAPSHOT} TIMESTAMP AS OF '{first[1]}' AS reported
    JOIN {SNAPSHOT} TIMESTAMP AS OF '{last[1]}' AS restated USING (day)
    ORDER BY day"""))
