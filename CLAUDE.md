# CLAUDE.md — databricks-retail-bank-lakehouse

> Workspace invariants live in the workspace `CLAUDE.md`. This file is only what is true here.

## What this repo is

A GraphL concept app: **learn Databricks by building a retail bank lakehouse**, `globalbank`,
the data platform of Global Bank (fictional), from a few files in a Volume to a governed, declared,
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

2026-10-26: infra ported, `globalbank_sim` built and verified, Course 1 authored. 2026-10-27: the
owner's Free Edition workspace connected (`DATABRICKS_HOST` / `DATABRICKS_TOKEN` as environment
secrets); Course 2 authored on it. The owner reviews at the end (2026-10-26: "do course by course
till end").

**The owner's workspace holds other catalogs** (personal and training ones). Never list catalogs,
groups or users unfiltered on screen: filter to `globalbank*`, or print our own objects only.
`spine.py` refuses to write a transcript holding even a fragment of a real identifier (a storage
path cut to 40 columns once kept the account id's first 11 characters).

| # | Course | Sections | Status |
| --- | --- | --- | --- |
| 1 | `intro` | 4 | authored, replayed (lab), rendered, looked at; no audio |
| 2 | `start` | 6 | pilot: authored, replayed on the workspace, rendered, looked at; no audio |
| 3 | `land` | 8 | authored, replayed on the workspace, rendered, looked at; no audio |
| 4 | `ledger` | 8 | replaying on the second workspace (steps 1–3 done); scenes drafted |
| 5 | `customers` | 8 | authored, replayed on the second workspace, rendered, looked at; no audio (5.8 documented) |
| 6 | `protect` | 8 | not started |
| 7 | `pipeline` | 9 | not started |
| 8 | `serve` | 7 | not started |
| 9 | `detect` | 8 | not started |
| 10 | `schedule` | 7 | not started |
| 11 | `ship` | 7 | not started |
| 12 | `operate` | 6 | not started |

## Workspace quotas (learned 2026-10-27)

Free Edition's metastore allows **50 volumes** and **500 tables**, and Unity Catalog keeps a dropped
managed volume (and table) for 7 days, **counting it against the quota all that time**. Course 2/3's
first replays reset with `databricks catalogs delete globalbank_dev --force` before every step; a
few dozen replays dropped ~40 volumes, the quota read 50/50 with 9 live, and every volume create was
refused (`QUOTA_EXCEEDED.UC_RESOURCE_QUOTA_EXCEEDED`) until those drops age out (~2026-11-03 to 05).
So:

- **A replay never drops the catalog, a schema or a volume.** `scripts/ws_reset.py` (every
  workspace step's first setup command) drops only tables and EMPTIES volumes.
- Tables still count when dropped: replay a course when it changed, not on every check.
- Check before a long replay: `databricks` SDK `resource_quotas.get_quota('metastore', <id>,
  'volume-quota')`; the count refreshes only on creates.

## The toolchain

CPython **3.12.15** as `python3.12` (`scripts/install-toolchain.sh`, also usable as the cloud
environment's setup script): databricks-connect 18.3 (serverless environment version 5) needs 3.12.
It does not relink `python` — the Spark course owns that on a shared machine; `spine.py` puts a
`python` → python3.12 link first on PATH inside a replay. Databricks CLI **1.22.1** (checked against
the release's SHA256SUMS) and **databricks-connect 18.3.7** (the project's `requirements.txt`; on the
workspace it reports Spark 4.2.0 on serverless). The generator is standard library only, so the
repo needs no venv of its own.

What the workspace taught the replay (Course 2):

- **The CLI notices an AI agent** (`CLAUDECODE`, `AI_AGENT`) and prints an "aitools" hint a learner
  never sees: `spine.py` drops the agent's own variables from the replay environment.
- **Normalising the email breaks column alignment** (it is shorter than the real one): never show the
  user inside a `show()` grid or a CLI table; print it as a line (2.3) or leave the command out (2.4
  dropped `databricks schemas list`, whose Owner column misaligned).
- **`databricks fs cp -r` copies in parallel** and prints in a different order every run: count it
  (`| wc -l`), never show it.
- **A cold serverless session takes ~30 s**; a course replays in a few minutes.
- The workspace and account ids come from `databricks auth describe -o json`, not the host.

## The data: `globalbank_sim`

A seeded generator of Global Bank's September and October (port of `shopwave_gen`): every source
drawn from its own random stream keyed by (seed, source, day), so a slice is byte-identical to the
same slice of a full run; the core system's history (changes need the state they change) is
computed once and cached. Every planted problem (the 14 October batch in cents, `wallet_type` on 15
October, the `"12,50"` partner rows, resends, late arrivals, reversals, clearing past month end, the
out-of-order CDC pair, the three card-testing rings and September's chargebacks, the skewed
supermarket, foreign spend, the erasure request) is a named constant in `model.py`, asserted by
`python3.12 -m globalbank_sim verify`. Change the generator only with `verify` green and every
spine step's `generated` check green. Identifiers use formats no country issues (`XN…` national
ids, the unassigned `ZZ` IBAN country, `@example.com` emails).

## The medallion layout

One schema per layer in each catalog (`globalbank_dev`, `globalbank_prod`): `landing` (Volumes) →
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

## The spine

`spine/<course>/<NN-step>/` = `project/` + `session.txt` + `step.json`, replayed by `scripts/spine.py`
exactly as in `spark-ecommerce-analytics` (`first` / `from` + `changes` / `lab`; generated data by
spec into `landing/`, never committed). Built: no JVM or jars; `{"workspace": true}` steps. What the
workspace adds:

- **The replay talks to a live workspace** through a CLI profile from the environment (host + token
  as secrets, never committed, never printed). Without them a workspace step cannot replay.
- **Normalisation**: the host is shown as `https://globalbank.cloud.databricks.com`, the user as
  `ana@globalbank.example`, local paths as `/home/ana/globalbank`. Normalise in the replay, never
  by hand in a scene.
- **Volatile by nature**: run ids, update ids, job ids, timestamps, durations, URLs. Masked in the
  comparison; a scene READS such a value from the session, and narration never says it.
- **Every step starts from a known workspace state**: a step's setup drops and recreates what it
  owns under `globalbank_dev`, so replays do not depend on order or on a previous run.
- **The daily fair-usage quota is a budget**: keep data small, and replay one course at a time.

## Frames

`spark-ecommerce-analytics`' IDE template, unchanged: explorer | editor (80 × 23) over terminal (13)
| fixed side pane. Every IDE side pane carries a diagram. No edges between panes. A detour (◆) that
cannot fit the side pane at ≥ 24px is a full concept scene with the real output inside it.
**The workspace UI is never screenshotted**: pipeline graphs, lineage, query profiles, job runs and
dashboards are drawn from the API's own numbers (event log, system tables, run output). graphl-flow's
Azure set has a `databricks` tile (used for the platform, as in 1.1); there is no Delta mark: lucide
`layers` for Delta, `spark` for Spark.

## Checks, before handing over

```sh
npm run build && npx tsc --noEmit && npm run check   # check-content + check-render (4K)
python3.12 scripts/spine.py <course>                 # workspace steps need DATABRICKS_HOST/TOKEN
python3.12 -m globalbank_sim verify
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
