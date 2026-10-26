# databricks-retail-bank-lakehouse

**Learn Databricks by building a retail bank lakehouse.** A GraphL concept app: one application,
`globalbank`, the data platform of Global Bank (fictional), grows from a few card files in a
Volume to a governed, declared, scheduled and tested lakehouse that serves finance, risk, branch
managers, the regulator and a fraud model. Every Databricks feature is taught at the moment the bank
needs it, in real code **run on a Databricks Free Edition workspace**. Scenes render with
`@graphlearning/graphl-flow`; the app shell is `@graphlearning/shell`.

Planned as **one video: "Learn Databricks by building a retail bank lakehouse: full course,
beginner to professional"** (~2 h 50 min, 12 courses, 85 sections). Prerequisite: the Spark series
(`spark-ecommerce-analytics`).

**Status:** Course 1 (`intro`) is authored; Courses 2–12 wait on access to a Databricks Free
Edition workspace. Scope, sections, data and run tiers are in [`COURSE-PLAN.md`](COURSE-PLAN.md);
authoring rules and per-course status are in [`CLAUDE.md`](CLAUDE.md).

## Run it

```sh
npm install
npm run dev          # http://localhost:5173  ·  routes are #/<course>-<section>
```

## Verify a change

```sh
scripts/install-toolchain.sh                          # once: CPython 3.12.15 as python3.12
npm run build && npx tsc --noEmit && npm run check    # check: content + 4K render
python3.12 scripts/spine.py                           # replays every step (workspace steps need credentials)
python3.12 -m globalbank_sim verify                   # every planted problem is in the data
npm run shots -- <course>                             # 4K PNGs in out/shots/, then look at them
```

## The architecture

A **medallion** lakehouse, one schema per layer in each catalog: `landing` (the files as sent) →
`bronze` (every record, append-only) → `silver` (typed, de-duplicated, validated entities) → `gold`
(balances, statements, fraud flags, the regulator's report). The layers also set who may read what
and what a full refresh may rebuild.

## The arc

| Global Bank needs to… | Databricks feature | Course |
| --- | --- | --- |
| query card files without running a cluster | serverless, Databricks Connect, Volumes | 2 `start` |
| ingest every new file exactly once | Auto Loader | 3 `land` |
| undo a bad batch and refuse the next | Delta: time travel, `RESTORE`, constraints | 4 `ledger` |
| keep customers current and historical | `MERGE`, SCD type 2, change data feed | 5 `customers` |
| protect national IDs, filter by branch | Unity Catalog: grants, masks, filters, lineage | 6 `protect` |
| stop hand-running notebooks | Lakeflow pipelines, expectations, `AUTO CDC` | 7 `pipeline` |
| answer "what did we report on 31 October?" | Databricks SQL, time travel | 8 `serve` |
| flag card fraud in minutes | Structured Streaming, MLflow | 9 `detect` |
| run nightly and recover from failure | Lakeflow Jobs | 10 `schedule` |
| deploy from git, tested | Declarative Automation Bundles, CI | 11 `ship` |
| see its cost and stay fast | system tables, liquid clustering | 12 `operate` |

## Layout

```
src/content/<course>/    one file per section + the course index
src/scenes/<course>/     declarative scenes (never x/y)
spine/<course>/<step>/   the app as real files, one cumulative snapshot per step
globalbank_sim/          the seeded data generator (owned, synthetic data)
scripts/                 spine.py, check-content, check-render, registry, shots
```
