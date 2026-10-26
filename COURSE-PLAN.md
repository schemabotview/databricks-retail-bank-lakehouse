# Learn Databricks by building a retail bank lakehouse: full course, beginner to professional — plan

**Status: v1 plan, awaiting owner review (2026-10-26).** Nothing is authored yet.

## The idea

One application, `quill-lakehouse`, the data platform of **Quill Bank**, a fictional retail bank.
It grows from a few files in a Volume to a governed, declarative, scheduled, tested lakehouse that
serves finance, risk, branches, the regulator and a fraud model. Every Databricks feature is taught
**when the bank first needs it**. Background (what the control plane is, what Unity Catalog's
object model is) appears as short detours (◆) at the moment it answers a question on screen.

Why Databricks exists is the course's spine, not its first lecture. Spark's authors founded the
company to run Spark for people who did not want to run clusters; Delta Lake came next because a
data lake of plain files cannot be trusted (no transactions, no updates, no schema); Unity Catalog
came after that because a lake nobody governs cannot hold anything sensitive. A bank hits each of
those walls in that order, so building one walks the platform's own history:

| The bank's wall | What Databricks built for it | Course |
| --- | --- | --- |
| Card and app events are too many for the warehouse, so they are dumped as files | Spark on managed, serverless compute; Auto Loader | 2, 3 |
| A bad processor batch corrupts the totals; a file cannot be rolled back | Delta Lake: transactions, constraints, time travel, `RESTORE` | 4 |
| Customers and accounts change in the core system every day, and their history matters | `MERGE`, SCD type 2, change data feed | 5 |
| National IDs and account numbers; branches that may see only their region | Unity Catalog: grants, masks, row filters, lineage, audit | 6 |
| A dozen hand-run notebooks, run in the wrong order once | Lakeflow pipelines (Spark Declarative Pipelines), expectations, `AUTO CDC` | 7 |
| "What did we report on 31 October?" | Databricks SQL, time travel as an audit tool | 8 |
| Card fraud must be flagged in minutes, not at month end | Structured Streaming + MLflow on the same governed tables | 9 |
| It has to run every night, and recover when one step fails | Lakeflow Jobs | 10 |
| A second engineer joins; prod was edited by hand | Declarative Automation Bundles, tests, CI | 11 |
| The bill, and the slowly degrading queries | System tables, liquid clustering, predictive optimization | 12 |

Why a retail bank:

- **Everyone has a bank account.** Cards, balances and statements need no domain lecture.
- **Every Databricks feature has a reason in a bank**: time travel answers the regulator, masks are
  required, history tables are the core of the job, fraud needs a stream, erasure has to be weighed
  against record retention.
- **It is where Databricks data engineers work.** Financial services is one of the platform's
  largest markets.
- **It grows the way a real platform does**: files → trusted tables → governed tables → a declared
  pipeline → a scheduled job → a deployed bundle.

## How this course differs from its siblings

- **`spark-ecommerce-analytics`** teaches Spark and open-source Delta on a laptop and a local
  cluster. This course assumes it: Spark's API, partitions, joins and Delta's log are referenced,
  never re-taught. What is new here is everything the *platform* adds.
- **`databricks-data-engineer-ct`** is the broad curriculum (13 courses, a retail chain, every
  platform feature documented beside local runs, because it was authored with no workspace). This
  course is one app, built end to end, **run on a real Databricks workspace** (Free Edition). Port
  its research and verification notes; do not repeat its scope.

## The platform: Databricks Free Edition, every output run

Free Edition is free, serverless-only, and has Unity Catalog, Lakeflow pipelines, Lakeflow Jobs,
Databricks SQL and MLflow, so almost every section can show a real run. Its limits shape the app
(checked against the Free Edition limitations page, updated 2026-10-18):

| Limit | What the course does about it |
| --- | --- |
| Serverless compute only, no custom clusters | Every run is serverless; classic clusters and cluster policies are documented (2.2) |
| One SQL warehouse, 2X-Small | Course 8 uses it; data sizes stay modest |
| One active pipeline per pipeline type | One pipeline, `quill_pipeline`, holds bronze → gold |
| Max 5 concurrent job tasks | The nightly job's widest fan-out is ≤ 5 tasks |
| No account console or account APIs; no SSO/SCIM | Account-level administration is documented; grants use what the workspace allows (see Open decisions) |
| Outbound internet limited to trusted domains | The workspace never fetches data; the generator runs on the laptop and uploads |
| Daily fair-usage quota | Data is sized to replay the whole course within one day's quota |
| Non-commercial use only | Fits a course; said once in 2.1 |

Every frame is in one tier, and says so when it is not the first:

1. **Run (workspace).** Executed on the owner's Free Edition workspace through the CLI or
   Databricks Connect; the frame shows what it printed. The default.
2. **Run (local).** Executed on the laptop: the generator, unit tests on local PySpark.
3. **Documented.** A feature Free Edition does not offer (classic clusters, account console,
   private networking, managed connectors if unavailable, CI with a service principal if
   unavailable). Checked against the live docs at authoring time, dated, and labelled on screen.
4. **Model.** A documented rule reproduced as a small program; it proves nothing about the platform
   and says so.

No prices are ever quoted; cost is shown in DBUs from `system.billing.usage`.

## Pinned versions

Pinned once the Course 2 infra is built, then never changed. Candidates at the time of writing:

| Tool | Candidate | Why |
| --- | --- | --- |
| Databricks CLI | latest at infra time | `auth`, `fs`, `bundle`, `pipelines`, `jobs` |
| `databricks-connect` | 19.3.x (PyPI latest, needs Python 3.12) | must match what Free Edition's serverless environment accepts — verified in 2.3, not assumed |
| Python | 3.12 | `databricks-connect` 19.3 requires `==3.12.*` |
| `databricks-sdk` | 0.157.x | statement execution, system tables, the event log |
| `pyspark` + `delta-spark` (tests only, separate venv) | 4.2.0 + 4.4.1 | the same pair as `spark-ecommerce-analytics`; Connect and PySpark cannot share a venv |
| `mlflow`, `scikit-learn` | at Course 9 | the fraud model |

## The bank and its data: `quill_sim`

All data is synthetic and owned, made by a seeded generator (ported from `shopwave_gen`): every
table drawn from its own random stream keyed by (seed, table, day), so a slice is byte-identical to
the same slice of a full run. The generator runs on the laptop and uploads to a Volume, which is
how the landing zone of a real bank is fed by a vendor or a CDC tool.

| Source | Arrives as | Shape | Like a real bank's |
| --- | --- | --- | --- |
| Card authorizations | JSON, one file every 5 minutes | `auth_id, card_id, merchant_id, mcc, amount, currency, ts, status` | card processor's feed |
| Settlements | CSV, once a day, 1–3 days late | `auth_id, settled_amount, settled_ts` | the scheme's clearing file |
| Core banking CDC | JSON change records | `op (I/U/D), seq, ts, table, before/after` for customers, accounts, KYC | a CDC tool reading the core system |
| Mobile app events | JSON | `session_id, customer_id, event, app_version, ts` | app telemetry |
| Reference | CSV | merchants, MCC codes, branches/regions, daily FX rates | reference data |

Sized to stay well inside the daily quota (order of magnitude: 5,000 customers, ~6,500 accounts,
~40 days of card authorizations, a few hundred thousand rows). Final sizes are frozen in Course 2.

**Planted problems**, each a named constant in `quill_sim/model.py` and asserted by `verify`:

- **The 14 October batch**: the processor sends one file in minor units (cents), so amounts are ×100. (4)
- **Resent authorizations**: identical duplicates in a later file. (3)
- **Late settlements** and **reversals** (refunds). (4)
- **The 15 October schema change**: the processor adds `wallet_type`. (3)
- **A partner feed with `"12,50"`** as an amount. (3)
- **Out-of-order CDC**: sequence 7 arrives before 6; a customer's address and KYC status change; an account closes (`D`). (5)
- **An erasure request** for one customer, against an illustrative record-retention rule. (6)
- **A card-testing ring**: many small authorizations on new merchants within minutes. (9)
- **Skew**: one supermarket chain is ~20% of transactions. (12)
- **Small files**: 5-minute landing becomes thousands of files. (12)
- **Foreign spend**: authorizations in USD and GBP, converted with the daily FX file. (8)

Regulatory rules and thresholds are **illustrative**, labelled so, and never legal advice.

## The app: `quill-lakehouse`

One name everywhere: the folder and the bundle are `quill-lakehouse`; the Python package is
`quill`; the catalogs are `quill_dev` and `quill_prod`. Paths are shown as
`/home/ana/quill-lakehouse`; Ana is Quill Bank's data engineer.

```
quill-lakehouse/
  pyproject.toml          databricks-connect, the quill package               (2 → 11)
  quill_sim/              the seeded generator (owned data)                   (2 →)
  src/quill/
    session.py            DatabricksSession on serverless                     (2)
    land.py               Auto Loader → bronze                                (3)
    ledger.py             settlements MERGE, constraints, restore             (4)
    cdc.py                core-system changes → SCD1 / SCD2                   (5)
    fraud/                rules.sql, features.py, train.py, score.py          (9)
  governance/             grants.sql, masks.sql, filters.sql, tags.sql        (6)
  pipelines/              quill_pipeline.py: bronze, silver, gold declared    (7)
  sql/                    balances.sql, statement.sql, as_of.sql, alerts      (8)
  dashboards/             statements.lvdash.json                              (8)
  resources/              quill_pipeline.yml, nightly.yml                     (7 → 11)
  databricks.yml          the bundle: targets dev, prod                       (11)
  tests/                  local PySpark unit tests, one Connect test          (11)
  .github/workflows/      deploy.yml                                          (11)
```

| After course | Quill Bank can… |
| --- | --- |
| 2 Start | query a day of card authorizations in a Delta table on serverless |
| 3 Land | ingest every new card file exactly once, surviving schema changes |
| 4 Ledger | undo a bad batch, refuse the next one, and settle authorizations |
| 5 Customers | keep customers, accounts and KYC current *and* historical |
| 6 Protect | mask PII, filter by branch region, show lineage and audit, honour erasure |
| 7 Pipeline | build bronze → silver → gold as one declared, checked pipeline |
| 8 Serve | publish balances, statements and an as-of report to analysts |
| 9 Detect | flag card testing in minutes, with a tracked, registered model |
| 10 Schedule | run every night, start on file arrival, repair a failed run |
| 11 Ship | deploy dev and prod from git, tested |
| 12 Operate | see its own cost and keep its tables fast |

## The courses

Side pane = the diagram (every IDE section carries one). Detours are marked ◆: a side-pane picture
of the code on screen, or a full concept scene (its own section, with the real output inside it)
when the picture cannot fit the side pane at ≥ 24px body text in the 4K frame. A tier other than
**Run (workspace)** is marked in the Step column.

**1. `intro` · Why Databricks, and Quill Bank · 3**

| # | Section | Frame | Scene |
| --- | --- | --- | --- |
| 1 | Why Databricks exists | concept | warehouse + lake + copies → the lakehouse; the walls table above, condensed |
| 2 | Quill Bank's data | concept | the five sources → who needs what: finance, risk, branches, regulator, data science |
| 3 | What we'll build | concept | **the app map**: sources → Volume → bronze → silver → gold → consumers; the finished statement first |

**2. `start` · A workspace and a first table · 6**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | A workspace and the CLI | `databricks auth login`, `databricks current-user me` | laptop → CLI → workspace REST API; the profile file |
| 2 | ◆ full scene: where your code runs | concept + lab (`current-user me`, `warehouses list`) | control plane → serverless compute → storage; classic clusters documented |
| 3 | Databricks Connect | `DatabricksSession.builder.serverless()`; `spark.range(3).show()` | the Spark API you know → Spark Connect → serverless |
| 4 | Catalogs, schemas, volumes | `quill_dev`, `raw`, the `landing` volume | catalog → schema → table / volume, a three-part name |
| 5 | Land the first files | `quill_sim` writes 1 October; `databricks fs cp` to the volume | laptop folder → `/Volumes/quill_dev/raw/landing/...` |
| 6 | The first table | `saveAsTable` → `bronze.card_auths`; `DESCRIBE HISTORY` | a managed Delta table: files + log, version 0 |

**3. `land` · Land the card stream · 8**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | Files keep arriving | re-reading the folder each run | plot: rows read per run vs new rows |
| 2 | Auto Loader | `cloudFiles`, `trigger(availableNow=True)` | new files → checkpoint → table |
| 3 | The checkpoint | run twice: 0 new; a deleted checkpoint duplicates | what the checkpoint remembers |
| 4 | Schema inference and hints | amounts as `DECIMAL(18,2)` via `schemaHints` | inferred vs hinted types |
| 5 | Schema evolution | 15 October adds `wallet_type`: the stream stops, then restarts with it | schema version 1 → 2 |
| 6 | Rescued data | `"12,50"` lands in `_rescued_data` | the row and its rescued JSON |
| 7 | Where each row came from | `_metadata.file_path`, `file_modification_time` | row → its source file |
| 8 | Bronze, reconciled | files landed = rows in bronze + resends + rescued | reconciliation table |

**4. `ledger` · Make the ledger trustworthy · 8**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | A bad batch lands | the 14 October file: daily spend ×100 | plot: daily card spend, the spike |
| 2 | Time travel | `VERSION AS OF` the version before it | the version list, one version lit |
| 3 | `RESTORE` | restore; the restore is itself a version | history: v5 bad → v6 restore |
| 4 | Constraints | `CHECK (amount < …)`, `NOT NULL`: the next file in cents is refused | write → refused, table unchanged |
| 5 | Two writers, one table | settlements and reversals commit at once | two commits, one retried |
| 6 | Settling authorizations | `MERGE` settlements: `AUTHORIZED → SETTLED / REVERSED`, late ones | `MERGE` paths: matched / not matched |
| 7 | Deletion vectors | a reversal marks rows instead of rewriting files | a data file + its deletion vector |
| 8 | Change data feed | `table_changes` for whoever reads next | change rows with `_change_type` |

**5. `customers` · Customers and accounts from the core system · 7**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | What the core system sends | CDC records: `op`, `seq`, before / after | one change record taken apart |
| 2 | Current state with `MERGE` | SCD type 1 customers | records → current table |
| 3 | Out of order | seq 7 before 6: a naive `MERGE` brings back an old address | two orderings, two results |
| 4 | Deletes | an account closes (`D`) | the row goes; the feed keeps it |
| 5 | History: SCD type 2 | address and KYC status with `valid_from` / `valid_to` | one customer's timeline |
| 6 | A point-in-time join | a September payment joined to the KYC status *then*, not now | two joins, two answers |
| 7 | Managed connectors | Lakeflow Connect from the core database (documented if Free Edition lacks it) | CDC tool → files vs connector → table |

**6. `protect` · Protect customers' data · 8**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | ◆ full scene: Unity Catalog | concept + lab (`SHOW CATALOGS`, `SHOW GRANTS`) | metastore → catalogs → schemas → objects; who needs what at Quill |
| 2 | Grants | `GRANT USE CATALOG, SELECT` to `finance`, `risk`, `branches` | the securable tree with grants |
| 3 | Column masks | national ID and IBAN masked unless `risk` | one query, two readers |
| 4 | Row filters | a branch manager sees their region only | rows kept per region |
| 5 | Tags and classification | `SET TAGS ('pii' = …)`; find every PII column | tagged columns |
| 6 | Lineage | `system.access.table_lineage`: bronze → gold | the lineage graph, from the query |
| 7 | Audit | `system.access.audit`: who read `customers` | audit rows |
| 8 | Erasure vs retention | PII vault keyed by token; erase the vault row, `VACUUM`; facts keep the token | vault ↔ facts, before / after |

**7. `pipeline` · Declare the pipeline · 9**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | Why declare | six hand-run notebooks; silver ran before bronze | run order by hand vs a dependency graph |
| 2 | Streaming tables | bronze as a streaming table over Auto Loader | append-only, incremental |
| 3 | Materialized views | gold daily spend | what a refresh recomputes |
| 4 | The graph | dependencies inferred from reads; drawn from the update's event log | the pipeline graph |
| 5 | Expectations | warn / drop / fail on amount and currency | rows kept under each policy |
| 6 | Quarantine | the failing rows kept, not lost | good / quarantine split |
| 7 | `AUTO CDC` | Course 5's `MERGE` as one declaration, SCD type 2 | before / after code |
| 8 | The event log | flow progress and expectation metrics | event-log rows |
| 9 | Full refresh | what it rebuilds; bronze protected from it | which tables a full refresh touches |

**8. `serve` · Serve the business · 7**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | A SQL warehouse | the 2X-Small warehouse, queried from the laptop | client → warehouse → tables |
| 2 | Daily balances | a running balance per account; FX conversion | plot: one account's October balance |
| 3 | The monthly statement | October statement per account | the statement, as a table |
| 4 | The regulator's question | "as reported on 31 October": `TIMESTAMP AS OF`, after late settlements | one date, two answers |
| 5 | A dashboard | `statements.lvdash.json`, drawn from its datasets' results | plot: spend by category, by region |
| 6 | Alerts | overdrafts above a threshold → notify | rule → condition → notification |
| 7 | Why a query is slow | query history: files read, bytes pruned | plot: files read per query |

**9. `detect` · Catch card fraud · 8**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | What card testing looks like | the planted ring | plot: one card's authorizations over 10 minutes |
| 2 | Rules first | > 5 authorizations in 10 minutes, in SQL | flagged rows |
| 3 | A streaming rule | windows + watermark over bronze; a flags table | window and watermark |
| 4 | Features in Unity Catalog | velocity, merchant novelty, amount z-score | feature table rows |
| 5 | MLflow tracking | a logistic regression on labelled September | run → params, metrics, model |
| 6 | A model in Unity Catalog | `quill_dev.ml.card_fraud@champion` | versions and the alias |
| 7 | Score the stream | the registered model inside the stream | stream → features → model → flags |
| 8 | Precision, recall, money | two thresholds: analysts' queue vs fraud caught | plot: the trade-off |

**10. `schedule` · Run it every night · 7**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | The nightly run | pipeline → statements → scoring → dashboard | the task graph |
| 2 | A job | create it, `databricks jobs run-now` | job → tasks → a run |
| 3 | File arrival | the settlement file lands → the job starts | trigger → run |
| 4 | Failure and repair | a bad FX file fails one task; repair re-runs it and what follows | task states before / after repair |
| 5 | Idempotency | a re-run statement task appends twice; fix it | rows after two runs |
| 6 | Parameters and task values | `run_date` in, a count out | values flowing between tasks |
| 7 | Who the job runs as | `run_as`, notifications on failure | identity of each run |

**11. `ship` · Ship it as code · 7**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | The workspace is not git | a click-created job drifted from the code | workspace vs repo |
| 2 | A bundle | `databricks bundle init`; `databricks.yml` | the bundle's parts |
| 3 | Resources | the pipeline, the job, the schemas, the dashboard | YAML → workspace resource |
| 4 | Targets | dev (prefixed, paused) and prod | one bundle → two targets |
| 5 | Validate, deploy, run | `bundle validate / deploy / run` | deploy flow |
| 6 | Tests | pytest on transforms with local PySpark (run local); one Connect test | the test pyramid |
| 7 | CI | GitHub Actions deploys on merge (documented if a service principal is unavailable) | PR → test → deploy |

**12. `operate` · Operate it, and pay for it · 6**

| # | Section | Step | Side pane |
| --- | --- | --- | --- |
| 1 | What it costs | `system.billing.usage` by job and pipeline, in DBUs | plot: DBUs per resource |
| 2 | Small files | thousands of 5-minute files; `OPTIMIZE` | files before / after |
| 3 | Liquid clustering | `CLUSTER BY (card_id, txn_date)`; the skewed merchant | files read before / after |
| 4 | Predictive optimization | what it runs for managed tables, and what it does not | its operations, from history |
| 5 | The finished bank | the whole bundle | **the app map**, every part lit |
| 6 | Where next | the ct course for breadth; Lakebase, Apps | each part of the bank → where it goes next |

**12 courses, 84 sections, ~2 h 50 min.**

## Packaging for YouTube

**One video: "Learn Databricks by building a retail bank lakehouse: full course, beginner to
professional"**, all 12 courses as one continuous story. A course is one chapter group and the
owner's review unit; a section (90–150 s) is one chapter, titled *feature: what the bank gets*
(e.g. "Auto Loader: every card file exactly once"). The video opens with the finished statement
dashboard and fraud flags (the payoff first). Each section can also go out as a Short.

## How a section teaches

Objective → mental model (side pane) → the code and its real result → a failure or alternative →
bridge. One step per section; failure is its own step with a real error. Narration explains, never
reads code aloud. A detour ◆ is ≤ 120 s and returns to the bank.

## Build order

1. Owner review of this plan, and the open decisions below.
2. Infra: port `spark-ecommerce-analytics`' IDE template, `spine.py`, checks, registry and shots;
   extend the replay to the workspace (CLI profile, normalisation, volatile masks); `quill_sim`.
3. Course 2 as the pilot → owner review.
4. Courses 1, 3–12 one at a time, each reviewed on its rendered routes, then narrated.
5. Record all 12 → assemble and publish the one video.

## Decisions

1. Bank: **Quill Bank** (fictional); app `quill-lakehouse`, package `quill`, catalogs
   `quill_dev` / `quill_prod`.
2. Platform: **Databricks Free Edition**, serverless only; every output run there unless tiered.
3. Prerequisite: the Spark series. Spark and open-source Delta are referenced, not re-taught.
4. One video, one continuous story: 12 courses.
5. The workspace UI is never screenshotted: graphs, lineage, profiles and dashboards are drawn from
   the API's own numbers.
6. Current product names, with the former name said once for recognition: Lakeflow pipelines
   (built on Spark Declarative Pipelines; formerly DLT), Lakeflow Jobs, Declarative Automation
   Bundles (formerly Databricks Asset Bundles), data profiling (formerly Lakehouse Monitoring).

## Open decisions (owner)

1. **Workspace access for replays.** The spine replays against a real workspace, so the authoring
   environment needs the owner's Free Edition host and a token (an environment secret) and network
   access to that host. Without it, workspace sections can be written but not replayed.
2. **Identities for Course 6.** Masks and filters need a second reader to show two answers. Options:
   a second user invited to the workspace, or workspace groups if Free Edition allows them in
   grants. To be checked in the infra step.
3. **Course 9 scope.** Fraud detection with MLflow is in, because data and AI on one platform is why
   Databricks exists; it can be cut to the rules-only sections (1–3) if the course should stay pure
   data engineering.
4. **Length.** 84 sections is ~25 minutes longer than the Python course. Candidates to cut: 5.7,
   8.7, 12.4.
