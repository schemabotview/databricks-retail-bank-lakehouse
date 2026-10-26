# CLAUDE.md — databricks-retail-bank-lakehouse

> Workspace invariants live in the workspace `CLAUDE.md`. This file is only what is true here.

## What this repo is

A GraphL concept app: **learn Databricks by building a retail bank lakehouse**, `lakehaven`,
the data platform of Lakehaven Bank (fictional), from a few files in a Volume to a governed, declared,
scheduled, tested lakehouse, **run on a real Databricks Free Edition workspace**. A **section** is
`(scene, narration)`: one full-screen 16:9 frame, one chapter of the video.

**`COURSE-PLAN.md` is the source of truth**: courses, sections, the bank's growth, the generator's
planted problems, the run tiers, the pinned versions, the packaging (one video) and the open
decisions. Author from it; change it first, never drift from it.

Engine `@graphlearning/graphl-flow` (^0.3.0), shell `@graphlearning/shell` (^1.0.2), both published
and pinned. Sister repos:

- **`spark-ecommerce-analytics`** — the prerequisite (Spark and open-source Delta, local). Its infra
  (IDE template, `spine.py`, checks, registry, shots, the seeded generator) is the one to port. Port
  from it; do not reinvent it. Do not re-teach what it teaches; reference it.
- **`databricks-data-engineer-ct`** — the broad Databricks curriculum, authored without a
  workspace. Its research notes and product-name decisions are the starting point for every
  platform claim here; its scope is not.

## Status

Plan v1 written 2026-10-26, awaiting owner review. No infra, scenes, spine or narration yet.

| # | Course | Sections | Status |
| --- | --- | --- | --- |
| 1 | `intro` | 4 | not started |
| 2 | `start` | 6 | not started (pilot) |
| 3 | `land` | 8 | not started |
| 4 | `ledger` | 8 | not started |
| 5 | `customers` | 7 | not started |
| 6 | `protect` | 8 | not started |
| 7 | `pipeline` | 9 | not started |
| 8 | `serve` | 7 | not started |
| 9 | `detect` | 8 | not started |
| 10 | `schedule` | 7 | not started |
| 11 | `ship` | 7 | not started |
| 12 | `operate` | 6 | not started |

## The medallion layout

One schema per layer in each catalog (`lakehaven_dev`, `lakehaven_prod`): `landing` (Volumes) →
`bronze` → `silver` → `gold`, plus `vault` (PII by token) and `ml`. A table's layer is decided in
`COURSE-PLAN.md`'s table list, never ad hoc; gold reads only silver, and consumers (dashboards,
`finance`, `branches`) read only gold. Each layer's promise (complete / correct / ready) is what a
scene about it must show.

## Route contract

`#/` catalog; `#/<courseId>-<sectionId>` a section; `?capture=1` and `window.__scene.plan()` come
from the shell. Do not reimplement the shell. Slug `databricks-retail-bank-lakehouse` is the vite
`base`, the path under `graphl.in` and the repo name. Brand `--brand: #FF3621` (Databricks
red-orange), as in `databricks-data-engineer-ct`.

## Run tiers: every output run, and said where it ran

1. **Run (workspace)** — the default. Executed on the owner's Free Edition workspace (serverless)
   through the Databricks CLI, Databricks Connect or the SDK.
2. **Run (local)** — the generator and the unit tests (local PySpark 4.2.0 + delta-spark 4.4.1, a
   separate venv: Connect and PySpark cannot share one).
3. **Documented** — what Free Edition does not offer. Checked against the live docs at authoring
   time (`docs.databricks.com` is reachable from the authoring environment as of 2026-10-26), dated
   in the commit, and labelled on screen.
4. **Model** — a documented rule reproduced as a small program; labelled; proves nothing about the
   platform.

Never quote prices: cost is DBUs from `system.billing.usage`. Regulatory rules and thresholds are
illustrative and labelled so; nothing is legal advice. Check Free Edition limits (one pipeline per
type, 5 concurrent job tasks, one 2X-Small warehouse, no account console) before designing a step
that could hit them.

## The spine (planned: port, then extend)

`spine/<course>/<NN-step>/` = `project/` + `session.txt` + `step.json`, replayed by `scripts/spine.py`
exactly as in `spark-ecommerce-analytics` (`first` / `from` + `changes` / `lab`; generated data by
spec, never committed). What the workspace adds:

- **The replay talks to a live workspace** through a CLI profile from the environment (host + token
  as secrets, never committed, never printed). Without them a workspace step cannot replay.
- **Normalisation**: the host is shown as `https://lakehaven.cloud.databricks.com`, the user as
  `ana@lakehavenbank.example`, local paths as `/home/ana/lakehaven`. Normalise in the replay, never
  by hand in a scene.
- **Volatile by nature**: run ids, update ids, job ids, timestamps, durations, URLs. Masked in the
  comparison; a scene READS such a value from the session, and narration never says it.
- **Every step starts from a known workspace state**: a step's setup drops and recreates what it
  owns under `lakehaven_dev`, so replays do not depend on order or on a previous run.
- **The daily fair-usage quota is a budget**: keep data small, and replay one course at a time.

## Frames

`spark-ecommerce-analytics`' IDE template, unchanged: explorer | editor (80 × 23) over terminal (13)
| fixed side pane. Every IDE side pane carries a diagram. No edges between panes. A detour (◆) that
cannot fit the side pane at ≥ 24px is a full concept scene with the real output inside it.
**The workspace UI is never screenshotted**: pipeline graphs, lineage, query profiles, job runs and
dashboards are drawn from the API's own numbers (event log, system tables, run output). There is no
`databricks` or `delta` brand mark in the engine: `spark` for Spark, lucide `layers` for Delta,
`cloud` for the platform.

## Checks, before handing over

```sh
npm run build && npx tsc --noEmit && npm run check   # check-content + check-render (4K)
python scripts/spine.py <course>                     # replays against the workspace
python -m lakehaven_sim verify
npm run shots -- <course>                            # then LOOK at out/shots/
```

Checks are a floor, not proof.

## Invariants

- Never write `x`/`y`; scenes are declarative. Highlights and folds are found by text (`lineOf`).
- Stylesheets in order: graphl-flow, shell, `./theme.css` last.
- No `file:` installs committed. No credentials, hosts or real emails committed.
- Current product names (Lakeflow pipelines, Lakeflow Jobs, Declarative Automation Bundles, data
  profiling); a former name is said once, for recognition.
- Narration: `.tts` → `.wav` via Colab + Chatterbox only. Audio at `public/audio/<course>/<id>.wav`.
- `SiteHeader` on the catalog page only.

## Working agreement

Author a whole course (scenes, spine, narration), render it, look, then hand over the routes. No
silent scaffolding. Say what was built, verified and left out, and which tier each frame is in.
