import type { SceneModel } from '@graphlearning/graphl-flow'
import { ideFrame, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { appMap } from '../map'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import cost1 from '../../../spine/operate/01-cost/project/globalbank/cost.py?raw'
import s1 from '../../../spine/operate/01-cost/session.txt?raw'
import optimize2 from '../../../spine/operate/02-small-files/project/globalbank/optimize.py?raw'
import s2 from '../../../spine/operate/02-small-files/session.txt?raw'
import cluster3 from '../../../spine/operate/03-liquid-clustering/project/globalbank/cluster.py?raw'
import s3 from '../../../spine/operate/03-liquid-clustering/session.txt?raw'
import predictive4 from '../../../spine/operate/04-predictive/project/globalbank/predictive.py?raw'
import s4 from '../../../spine/operate/04-predictive/session.txt?raw'
import statement from '../../../spine/serve/03-statements/session.txt?raw'
import flags from '../../../spine/detect/07-score/session.txt?raw'

// Course 12 — Operate it, and pay for it. 12.1–12.4 are workspace runs (spine/operate/); 12.5 is
// the app map with the finished bank's real output (from Courses 8 and 9's sessions); 12.6 is a
// documented map of where each part goes next.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const FILL = { spread: true, minH: 520 } as const
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', 'globalbank/session.py', 'globalbank/land.py', ...files, 'pipelines/', 'resources/', 'databricks.yml'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const T = 'globalbank_dev.bronze.card_auths'

// §1 — what it costs: DBUs by product, from system.billing.usage.
const out1 = outputOf(s1, 'python -m globalbank.cost')
const total1 = out1.match(/^([\d.]+) DBUs in 7 days/m)![1]
const rows1 = all(out1, /^\s+(\S+)\s+(\S+)\s+([\d.]+)$/gm).map((m) => ({ product: m[1], sku: m[2], dbus: Number(m[3]) }))
const top1 = Math.ceil(Math.max(...rows1.map((r) => r.dbus)) / 5) * 5 || 5
const cost1Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/cost.py'], 'globalbank/cost.py', ['globalbank/cost.py']),
  editor: { file: 'globalbank/cost.py', code: cost1, highlight: linesFrom(cost1, 'SELECT billing_origin_product', 'GROUP BY ALL ORDER BY dbus DESC') },
  session: s1,
  side: [
    {
      type: 'plot', id: 'dbus', compact: true, title: `${total1} DBUs in 7 days, by product`,
      x: { labels: rows1.map((r) => r.product.toLowerCase().replace(/_/g, ' ')) }, y: { min: 0, max: top1, step: top1 / 4 },
      series: [{ kind: 'bar', points: rows1.map((r, i) => [i, r.dbus] as [number, number]), tone: 'consume' }],
    },
    {
      type: 'table', id: 'what', title: 'Where the DBUs went', tone: 'consume', columns: ['product', 'what in this course'], rows: [
        { id: 'w-int', cells: ['INTERACTIVE', 'Databricks Connect: every script'] },
        { id: 'w-dlt', cells: ['DLT', 'globalbank_pipeline (Course 7)'] },
        { id: 'w-sql', cells: ['SQL', 'the warehouse: gold (Course 8)'] },
        { id: 'w-jobs', cells: ['JOBS', 'the nightly job (Course 10)'] },
      ],
    },
    { type: 'note', id: 'note', tone: 'consume', text: 'Cost is shown in DBUs, the platform’s own unit, from the bill’s system table. Prices depend on the contract and the cloud, so this course never quotes them.' },
  ],
})

// §2 — small files: one Auto Loader run per day wrote many small files; OPTIMIZE compacts them.
const files2 = s2.split(/^\$ /m).slice(1).filter((b) => b.startsWith('python -m globalbank.files')).map((b) => {
  const m = b.match(/: (\d+) files, ([\d.]+) MB, (\d+) KB a file/)!
  return { files: Number(m[1]), mb: m[2], kb: Number(m[3]) }
})
const opt2 = outputOf(s2, `python -m globalbank.optimize ${T}`).match(/(\d+) files removed, (\d+) added/)!
const small2: SceneModel = ideFrame({
  tree: tree(['globalbank/files.py', 'globalbank/optimize.py'], 'globalbank/optimize.py', ['globalbank/files.py', 'globalbank/optimize.py']),
  editor: { file: 'globalbank/optimize.py', code: optimize2, highlight: [linesFrom(optimize2, "m = get_spark().sql(f'OPTIMIZE {table}')")[0]] },
  session: s2,
  side: [
    {
      type: 'plot', id: 'files', compact: true, title: 'bronze.card_auths: data files',
      x: { labels: ['7 daily runs', 'after OPTIMIZE'] }, y: { min: 0, max: Math.ceil(files2[0].files / 5) * 5 || 5, step: (Math.ceil(files2[0].files / 5) * 5 || 5) / 5 },
      series: [{ kind: 'bar', points: [[0, files2[0].files], [1, files2[1].files]], tone: 'store' }],
    },
    {
      type: 'table', id: 'sizes', title: `OPTIMIZE: ${opt2[1]} removed, ${opt2[2]} added`, tone: 'store', columns: ['', 'files', 'MB', 'KB a file'], rows: [
        { id: 's-before', cells: ['before', String(files2[0].files), files2[0].mb, String(files2[0].kb)] },
        { id: 's-after', cells: ['after', String(files2[1].files), files2[1].mb, String(files2[1].kb)], tone: 'store' },
      ],
    },
    { type: 'note', id: 'note', tone: 'store', text: 'Every file a query opens costs a request and a footer read. A stream that lands every 15 minutes writes small files all day; compaction is the price of fresh data, paid later and in bulk.' },
  ],
})

// §3 — liquid clustering: the same query, files read by layout.
const out3 = outputOf(s3, 'python -m globalbank.cluster')
const read3 = all(out3, /^silver\.auths_(\w+)\s+files read\s+(\d+), skipped\s+(\d+)$/gm).map((m) => ({ t: m[1], read: Number(m[2]), skipped: Number(m[3]) }))
const cluster3Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/cluster.py', 'globalbank/optimize.py'], 'globalbank/cluster.py', ['globalbank/cluster.py']),
  editor: { file: 'globalbank/cluster.py', code: cluster3, highlight: linesFrom(cluster3, "for name, layout in (('by_arrival', ''), ('clustered',", "'CLUSTER BY (merchant_id, auth_ts)')):") },
  session: s3,
  side: [
    {
      type: 'plot', id: 'read', compact: true, title: 'One merchant, one day: files read and skipped',
      x: { labels: read3.map((r) => r.t.replace('_', ' ')) }, y: { min: 0, max: Math.max(5, ...read3.map((r) => r.read + r.skipped)), step: 1 },
      series: [
        { kind: 'bar', label: 'read', points: read3.map((r, i) => [i, r.read] as [number, number]), tone: 'consume' },
        { kind: 'bar', label: 'skipped', points: read3.map((r, i) => [i, r.skipped] as [number, number]), tone: 'store' },
      ],
    },
    {
      type: 'group', id: 'how', title: 'CLUSTER BY (merchant_id, auth_ts)', icon: 'layers', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'h-skew', title: 'M0001: one supermarket, ~20% of rows', sub: 'by arrival, it is in every file', icon: 'building' },
        { type: 'item', id: 'h-cluster', title: 'clustered: rows with near keys together', sub: 'each file covers a narrow range', icon: 'layers' },
        { type: 'item', id: 'h-skip', title: 'the query skips the other files', sub: 'by their min / max statistics', icon: 'filter' },
      ],
    },
  ],
  edges: [
    { from: 'h-skew', to: 'h-cluster', label: 'OPTIMIZE' },
    { from: 'h-cluster', to: 'h-skip' },
  ],
})

// §4 — predictive optimization: on, and what it has run.
const out4 = outputOf(s4, 'python -m globalbank.predictive')
const po4 = out4.split('\n').find((l) => l.startsWith('Predictive')) ?? 'Predictive Optimization: (not reported)'
const ops4 = all(out4, /^\s{2}(\w+)\s+(\d+)$/gm).map((m) => ({ op: m[1], n: m[2] }))
const hist4 = (out4.match(/by operation: (.*)$/m)?.[1] ?? '').split(', ').filter(Boolean)
const predictive4Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/cluster.py', 'globalbank/predictive.py'], 'globalbank/predictive.py', ['globalbank/predictive.py']),
  editor: { file: 'globalbank/predictive.py', code: predictive4, highlight: linesFrom(predictive4, 'FROM system.storage.predictive_optimization_operations_history', "WHERE catalog_name = 'globalbank_dev'") },
  session: s4,
  side: [
    {
      type: 'table', id: 'state', title: po4.split(':')[0], tone: 'infra', columns: ['setting', 'value'], rows: [
        { id: 'p-on', cells: ['silver schema', po4.split(': ').slice(1).join(': ')], tone: 'infra' },
        ...ops4.map((o) => ({ id: `p-${o.op}`, cells: [o.op, o.n] })),
        ...hist4.map((h, i) => ({ id: `h-${i}`, cells: ['auths_clustered history', h] })),
      ],
    },
    {
      type: 'table', id: 'who', title: 'Who runs what (documented)', tone: 'infra', columns: ['task', 'by hand (12.2, 12.3)', 'predictive optimization'], rows: [
        { id: 'w-opt', cells: ['compact small files', 'OPTIMIZE', 'runs it when it pays'] },
        { id: 'w-cl', cells: ['cluster', 'CLUSTER BY + OPTIMIZE', 'clusters as it compacts'] },
        { id: 'w-vac', cells: ['remove old files', 'VACUUM', 'runs it, after retention'] },
        { id: 'w-stats', cells: ['statistics', 'ANALYZE', 'keeps them current'] },
      ],
    },
  ],
})

// §5 — the finished bank: the app map, every part lit, with its real output.
const stmt = all(outputOf(statement, 'python -m globalbank.warehouse sql/gold/statement_of.sql account=A0000011'), /^(\S.*?)\s{2,}(-?[\d,.]+)$/gm)
  .map((m) => ({ line: m[1], eur: m[2] })).filter((r) => r.line !== 'line')
const flagged = outputOf(flags, 'python -m globalbank.score 2026-10-22 0.9').split('\n')[0]
const finished5: SceneModel = appMap({
  title: 'The finished bank',
  sub: 'every part built, run on Free Edition: sources → landing → bronze → silver → gold → consumers',
  built: 12,
  output: {
    type: 'group', id: 'm-out', bare: true, children: [
      {
        type: 'table', id: 'm-stmt', title: 'A0000011, October (Course 8)', tone: 'serve', columns: ['', 'EUR'],
        rows: stmt.filter((r) => r.line !== 'check').map((r, i) => ({ id: `st-${i}`, cells: [r.line, r.eur] })),
      },
      { type: 'item', id: 'm-flags', title: 'fraud flags (Course 9)', sub: flagged, icon: 'shield', tone: 'consume' },
    ],
  },
})

// §6 — where next: documented, each part of the bank → the product that takes it further.
const next6: SceneModel = {
  title: 'Where next',
  sub: 'documented (docs.databricks.com, checked 2026-10-27): what this course left out, by the part of the bank it extends',
  nodes: [
    {
      type: 'table', id: 'next', columns: ['the bank’s part', 'next', 'on Free Edition'], rows: [
        { id: 'n-serve', cells: ['gold, for people who do not write SQL', 'Genie: questions in plain language over gold', 'yes'], tone: 'serve' },
        { id: 'n-app', cells: ['a branch’s customer screen', 'Databricks Apps, reading gold', 'yes, up to 3 apps'] },
        { id: 'n-oltp', cells: ['a balance that must be exact now', 'Lakebase: Postgres beside the lakehouse', 'yes, 1 project'] },
        { id: 'n-model', cells: ['the fraud model, called per payment', 'Model Serving: an endpoint for @champion', 'limited'] },
        { id: 'n-mon', cells: ['silver’s quality, watched', 'data profiling (formerly Lakehouse Monitoring)', 'check the docs'] },
        { id: 'n-share', cells: ['statements to a partner bank', 'Delta Sharing', 'check the docs'] },
        { id: 'n-breadth', cells: ['every other platform feature', 'the companion course: databricks-data-engineer-ct', '—'], tone: 'infra' },
      ],
    },
  ],
}

export const operateScenes: Record<string, SceneModel> = {
  'operate-cost': cost1Scene,
  'operate-small-files': small2,
  'operate-liquid-clustering': cluster3Scene,
  'operate-predictive': predictive4Scene,
  'operate-finished': finished5,
  'operate-next': next6,
}
