"""The regulator's question: the report as it stood then, and as it is now."""
from globalbank.warehouse import run, show
from databricks.sdk import WorkspaceClient

SNAPSHOT = 'globalbank_dev.gold.regulatory_snapshot'

w = WorkspaceClient()
_, history = run(w, f'DESCRIBE HISTORY {SNAPSHOT}')
first, last = history[-1], history[0]  # newest first
for label, version in (('as reported', first), ('as restated', last)):
    print(f'{label}: version {version[0]}, written {version[1][:16]}')
    show(*run(w, f"""SELECT day, approved, cleared, cleared_eur
                     FROM {SNAPSHOT} TIMESTAMP AS OF '{version[1]}'
                     ORDER BY day"""))
