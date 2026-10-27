# drafts

Not part of the course. Scratch builders that write spine steps, kept so the work survives a fresh
session. Nothing here is replayed, rendered or checked.

- `build_c3.py` — how `spine/land/*` (Course 3) was assembled from `spine/start/06`. Course 3 is
  authored and replayed; this is only its history.
- `build_c4.py` (+ `statuses.tpl`, `changes.tpl`) — Course 4 (`ledger`), eight steps, **written but
  never replayed**: the first replay hit the metastore's volume quota (CLAUDE.md, "Workspace
  quotas"). Run it from this folder (`python3 build_c4.py`; it writes `spine/ledger/`), then
  `python3.12 scripts/spine.py --write ledger/`, once a volume can be created again.
