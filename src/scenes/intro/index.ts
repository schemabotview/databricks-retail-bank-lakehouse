import type { SceneModel } from '@graphlearning/graphl-flow'
import { appMap } from '../map'
import { outputOf } from '../lab'
import landed from '../../../spine/intro/01-landing/session.txt?raw'

// Course 1 — Why Databricks, and Global Bank. Four concept scenes. 1.1 is DOCUMENTED (the platform's
// history, from Databricks' docs and the 2021 lakehouse paper); 1.2 and 1.3 carry the lab's real
// output (spine/intro/01-landing: the generator's two months, landed); 1.4 is the plan's map. The
// finished bank's real output joins 1.4 once Course 12 runs (COURSE-PLAN.md, "Build order").
const stats = outputOf(landed, 'python what_landed.py')
const record = outputOf(landed, 'head -n 1 landing/card_auths/2026-10-15/auths-0900.json | python -m json.tool')
const count = (source: string) => stats.match(new RegExp(`^${source}\\s+(\\d+)\\s+([\\d,]+)`, 'm'))!.slice(1)
const [authFiles, auths] = count('card_auths')

const why: SceneModel = {
  title: 'Why Databricks exists',
  sub: 'every product answers a wall that teams hit, in the order they hit them',
  dir: 'row',
  nodes: [
    {
      type: 'group', id: 'before', badge: 1, title: 'Two systems', sub: 'how data teams worked', icon: 'server', tone: 'source', children: [
        { type: 'item', id: 'warehouse', title: 'a data warehouse', sub: 'SQL, transactions, governance; costly at volume, closed formats', icon: 'database' },
        { type: 'item', id: 'lake', title: 'a data lake', sub: 'cheap files at any volume; no transactions, no updates, no schema', icon: 'folder' },
        { type: 'item', id: 'copies', title: 'copies between them', sub: 'nightly ETL; two versions of every number', icon: 'workflow' },
      ],
    },
    {
      type: 'group', id: 'built', badge: 2, title: 'What Databricks built', sub: 'each answer, and the wall it removed', icon: 'databricks', tone: 'infra', children: [
        {
          type: 'table', id: 'history', columns: ['when', 'answer', 'the wall'],
          rows: [
            { id: 'h-2013', cells: ['2013', 'the company, by Spark’s creators', 'running Spark yourself'] },
            { id: 'h-2019', cells: ['2019', 'Delta Lake, open source', 'files with no transactions'] },
            { id: 'h-2021', cells: ['2021', 'the lakehouse paper', 'two systems, two copies'] },
            { id: 'h-uc', cells: ['2021–24', 'Unity Catalog, open-sourced 2024', 'a lake nobody governs'] },
            { id: 'h-run', cells: ['since', 'serverless, Lakeflow, Databricks SQL', 'running and operating it'] },
          ],
        },
        { type: 'note', id: 'history-note', tone: 'infra', text: 'Documented, not run: from Databricks’ own documentation and the 2021 CIDR lakehouse paper.' },
      ],
    },
    {
      type: 'group', id: 'lakehouse', badge: 3, title: 'The lakehouse', sub: 'one copy, open, governed', icon: 'layers', tone: 'store', children: [
        { type: 'item', id: 'lh-files', title: 'open files in your storage', sub: 'Parquet: any engine can read them', icon: 'cloud' },
        { type: 'item', id: 'lh-log', title: 'a transaction log', sub: 'Delta: commits, updates, history', icon: 'layers' },
        { type: 'item', id: 'lh-catalog', title: 'one catalog', sub: 'Unity Catalog: names, grants, lineage', icon: 'lock' },
        { type: 'item', id: 'lh-compute', title: 'any compute on top', sub: 'SQL, Python, streaming, ML', icon: 'cpu' },
      ],
    },
  ],
  edges: [
    { from: 'before', to: 'built', label: 'walls' },
    { from: 'built', to: 'lakehouse', label: 'answers' },
  ],
}

const bank: SceneModel = {
  title: 'Global Bank’s data',
  sub: 'two months of a fictional retail bank, generated and landed: every number here is the lab’s real run',
  dir: 'row',
  nodes: [
    {
      type: 'group', id: 'sources', badge: 1, title: 'Who sends what', sub: 'systems and vendors, as files', icon: 'server', tone: 'source', children: [
        { type: 'item', id: 's-cards', title: 'card processor', sub: 'authorizations: JSON lines, a file every 15 minutes', icon: 'card' },
        { type: 'item', id: 's-clear', title: 'card scheme', sub: 'settlements: one CSV a day, 1–3 days late', icon: 'building' },
        { type: 'item', id: 's-core', title: 'core banking, via CDC', sub: 'customers and accounts: every change, as JSON', icon: 'database' },
        { type: 'item', id: 's-post', title: 'core banking postings', sub: 'salary, rent, transfers: a CSV a day', icon: 'file' },
        { type: 'item', id: 's-app', title: 'the mobile app', sub: 'events: JSON lines, hourly', icon: 'screen' },
        { type: 'item', id: 's-other', title: 'and the rest', sub: 'FX rates, merchants, chargebacks, privacy requests', icon: 'folder' },
      ],
    },
    {
      type: 'group', id: 'landed', badge: 2, title: 'What landed', sub: `${Number(authFiles).toLocaleString('en')} card files alone`, icon: 'terminal', tone: 'ingest', children: [
        { type: 'code', id: 'stats', terminal: true, filename: 'terminal — globalbank', code: `$ python what_landed.py\n${stats}` },
        { type: 'note', id: 'stats-note', tone: 'ingest', text: `${auths} card authorizations in two months, from 5,000 customers. Synthetic: no real person, card or account.` },
      ],
    },
    {
      type: 'group', id: 'needs', badge: 3, title: 'Who needs what', sub: 'the teams the lakehouse serves', icon: 'users', tone: 'serve', children: [
        {
          type: 'table', id: 'teams', columns: ['team', 'needs', 'when'],
          rows: [
            { id: 't-finance', cells: ['finance', 'balances, statements', 'every morning'] },
            { id: 't-risk', cells: ['risk', 'fraud flags', 'within minutes'] },
            { id: 't-branch', cells: ['branches', 'their region only', 'every morning'] },
            { id: 't-reg', cells: ['regulator', 'figures as reported', 'on any past date'] },
            { id: 't-ds', cells: ['data science', 'labelled fraud', 'to train a model'] },
          ],
        },
        { type: 'note', id: 'teams-note', tone: 'serve', text: 'Five teams, five speeds, one copy of the data: the job the lakehouse is built for.' },
      ],
    },
  ],
  edges: [
    { from: 'sources', to: 'landed', label: 'land' },
    { from: 'landed', to: 'needs', label: 'serve' },
  ],
}

const medallion: SceneModel = {
  title: 'The medallion architecture',
  sub: 'four layers, each a stronger promise; one schema per layer in every catalog',
  nodes: [
    {
      type: 'group', id: 'layers', bare: true, dir: 'row', children: [
        {
          type: 'group', id: 'l-landing', title: 'landing', sub: 'the files, as sent', icon: 'folder', tone: 'source', children: [
            { type: 'code', id: 'record', lang: 'text', filename: 'one card authorization', code: record },
            { type: 'item', id: 'l-landing-why', title: 'kept, never edited', sub: 'any table can be rebuilt from here', icon: 'cloud' },
          ],
        },
        {
          type: 'group', id: 'l-bronze', title: 'bronze', sub: 'promise: complete', icon: 'layers', tone: 'infra', spread: true, children: [
            { type: 'item', id: 'b-what', title: 'every record received', sub: 'append-only, plus its file and arrival time', icon: 'stream' },
            { type: 'item', id: 'b-tables', title: 'card_auths, settlements', sub: 'core_cdc, postings, app_events', icon: 'table' },
            { type: 'item', id: 'b-who', title: 'read by engineers', icon: 'user' },
          ],
        },
        {
          type: 'group', id: 'l-silver', title: 'silver', sub: 'promise: correct', icon: 'layers', tone: 'ingest', spread: true, children: [
            { type: 'item', id: 's-what', title: 'one row per real thing', sub: 'typed, de-duplicated, validated; rejects quarantined', icon: 'check' },
            { type: 'item', id: 's-tables', title: 'card_transactions', sub: 'customers (+ history), accounts, merchants, fx_rates', icon: 'table' },
            { type: 'item', id: 's-who', title: 'read by engineers, risk, data science', icon: 'users' },
          ],
        },
        {
          type: 'group', id: 'l-gold', title: 'gold', sub: 'promise: ready', icon: 'layers', tone: 'store', spread: true, children: [
            { type: 'item', id: 'g-what', title: 'named for the business', sub: 'one table per use', icon: 'chart' },
            { type: 'item', id: 'g-tables', title: 'daily_balances, statements', sub: 'card_spend_daily, fraud_flags, regulatory_snapshot', icon: 'table' },
            { type: 'item', id: 'g-who', title: 'read by finance, branches, the regulator', icon: 'building' },
          ],
        },
      ],
    },
    {
      type: 'group', id: 'rules', bare: true, dir: 'row', children: [
        {
          type: 'group', id: 'decides', title: 'The layers also decide', icon: 'settings', tone: 'neutral', children: [
            {
              type: 'table', id: 'decide', columns: ['', 'bronze', 'silver', 'gold'],
              rows: [
                { id: 'd-grants', cells: ['who may read', 'engineers', '+ risk, data science', '+ finance, branches'] },
                { id: 'd-refresh', cells: ['a full refresh', 'never rebuilt', 'rebuilt from bronze', 'rebuilt from silver'] },
                { id: 'd-pii', cells: ['personal data', 'as received', 'masked', 'masks inherited'] },
              ],
            },
          ],
        },
        {
          type: 'group', id: 'beside', title: 'A convention, not a feature', icon: 'layers', tone: 'neutral', children: [
            { type: 'item', id: 'beside-vault', title: 'beside the layers: vault and ml', sub: 'personal data by token; features and models', icon: 'lock' },
            { type: 'item', id: 'beside-skip', title: 'skip a layer when it promises nothing new', sub: 'reference data goes straight to silver', icon: 'zap' },
          ],
        },
      ],
    },
  ],
  edges: [
    { from: 'l-landing', to: 'l-bronze', label: 'ingest' },
    { from: 'l-bronze', to: 'l-silver', label: 'clean' },
    { from: 'l-silver', to: 'l-gold', label: 'shape' },
  ],
}

const map: SceneModel = appMap({
  title: 'What we’ll build',
  sub: 'globalbank: Global Bank’s lakehouse, on a Databricks Free Edition workspace, one course at a time',
})

export const introScenes: Record<string, SceneModel> = {
  'intro-why': why,
  'intro-bank': bank,
  'intro-medallion': medallion,
  'intro-map': map,
}
