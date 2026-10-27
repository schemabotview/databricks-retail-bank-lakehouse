import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import nightly1 from '../../../spine/pipeline/01-why-declare/project/nightly.sh?raw'
import s1 from '../../../spine/pipeline/01-why-declare/session.txt?raw'
import bronze2 from '../../../spine/pipeline/02-streaming-tables/project/pipelines/bronze.py?raw'
import s2 from '../../../spine/pipeline/02-streaming-tables/session.txt?raw'
import gold3 from '../../../spine/pipeline/03-materialized-views/project/pipelines/gold.py?raw'
import s3 from '../../../spine/pipeline/03-materialized-views/session.txt?raw'
import graph4 from '../../../spine/pipeline/04-graph/project/globalbank/graph.py?raw'
import s4 from '../../../spine/pipeline/04-graph/session.txt?raw'
import silver5 from '../../../spine/pipeline/05-expectations/project/pipelines/silver.py?raw'
import s5 from '../../../spine/pipeline/05-expectations/session.txt?raw'
import silver6 from '../../../spine/pipeline/06-quarantine/project/pipelines/silver.py?raw'
import s6 from '../../../spine/pipeline/06-quarantine/session.txt?raw'
import silver7 from '../../../spine/pipeline/07-auto-cdc/project/pipelines/silver.py?raw'
import s7 from '../../../spine/pipeline/07-auto-cdc/session.txt?raw'
import events8 from '../../../spine/pipeline/08-event-log/project/globalbank/events.py?raw'
import s8 from '../../../spine/pipeline/08-event-log/session.txt?raw'
import bronze9 from '../../../spine/pipeline/09-full-refresh/project/pipelines/bronze.py?raw'
import s9 from '../../../spine/pipeline/09-full-refresh/session.txt?raw'

// Course 7 — Declare the pipeline: the whole medallion as one Lakeflow pipeline, run on the owner's
// Free Edition workspace (spine/pipeline/). Graphs, rows and expectation counts are read from the
// pipeline's own event log, never from a screenshot of its UI.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const num = (s: string) => Number(s.replace(/,/g, ''))
const fmt = (n: number) => n.toLocaleString('en')
const FILL = { spread: true, minH: 520 } as const
const PIPES = ['pipelines/bronze.py', 'pipelines/silver.py', 'pipelines/gold.py']
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...files.filter((f) => f.startsWith('pipelines/')),
      'globalbank/__init__.py', 'globalbank/session.py', ...files.filter((f) => !f.startsWith('pipelines/')), 'land.sh'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const RUN = 'python -m globalbank.run'
type Row = { name: string; rows: number; how?: string }
const runs = (session: string): Row[][] => session.split(/^\$ /m).slice(1).filter((b) => b.startsWith(RUN))
  .map((b) => all(b, /^\s+(\S+)\s+([\d,]+) rows(?:\s+\((.+)\))?$/gm).map((m) => ({ name: m[1], rows: num(m[2]), how: m[3] })))
const layerTone = (n: string) => (n.startsWith('bronze') ? 'ingest' : n.startsWith('silver') ? 'store' : 'consume') as 'ingest' | 'store' | 'consume'
const nid = (n: string) => `n-${n.replace(/[^a-z0-9]+/gi, '-')}`

// §1 — why declare: the nightly run by hand, in the order typed; silver ran before bronze.
const night = outputOf(s1, 'bash nightly.sh 2026-10-02').split('\n')
const silverBefore = rowsIn(night.find((l) => l.includes('silver.card_transactions'))!)
const bronzeLine = night.find((l) => l.includes('bronze.card_auths'))!
const added = num(bronzeLine.match(/\+ ([\d,]+) =/)![1])
const silverAfter = rowsIn(outputOf(s1, 'python -m globalbank.ledger post 2026-10-02'))
function rowsIn(line: string) { return num(line.match(/([\d,]+) rows/)![1]) }
const why1: SceneModel = ideFrame({
  tree: tree(['globalbank/cdc.py', 'globalbank/land.py', 'globalbank/ledger.py', 'nightly.sh'], 'nightly.sh', ['nightly.sh']),
  editor: { file: 'nightly.sh', code: nightly1, lang: 'shell', highlight: linesFrom(nightly1, 'python -m globalbank.ledger post', 'python -m globalbank.land  ') },
  session: s1,
  side: [
    {
      type: 'table', id: 'order', title: 'The order typed vs the order needed', tone: 'consume', columns: ['typed', 'reads', 'needed'], rows: [
        { id: 'o-1', cells: ['1  ledger post', 'bronze.card_auths', '3'], tone: 'consume' },
        { id: 'o-2', cells: ['2  land', 'the volume', '1'] },
        { id: 'o-3', cells: ['3  land core_cdc', 'the volume', '2'] },
        { id: 'o-4', cells: ['4  cdc customers', 'bronze.core_cdc', '4'] },
      ],
    },
    {
      type: 'plot', id: 'rows', compact: true, title: 'silver.card_transactions, rows',
      x: { labels: ['before', 'after nightly.sh', 'posted again'] }, y: { min: 0, max: Math.ceil(silverAfter / 5000) * 5000, step: 2500 },
      series: [{ kind: 'bar', points: [[0, silverBefore], [1, silverBefore], [2, silverAfter]], tone: 'consume' }],
    },
    { type: 'note', id: 'note', tone: 'consume', text: `Bronze took ${fmt(added)} new authorizations, but the silver step had already run: 2 October stayed out of silver until someone noticed and ran it again.` },
  ],
})

// §2 — streaming tables: bronze, declared; the pipeline reads only new files.
const r2 = runs(s2)
const deployed2 = outputOf(s2, 'python -m globalbank.deploy')
const files2 = outputOf(s2, 'bash land.sh 2026-10-02 | wc -l').trim()
const streaming2: SceneModel = ideFrame({
  tree: tree(['pipelines/bronze.py', 'globalbank/deploy.py', 'globalbank/run.py'], 'pipelines/bronze.py', ['pipelines/bronze.py', 'globalbank/deploy.py', 'globalbank/run.py']),
  editor: { file: 'pipelines/bronze.py', code: bronze2, ...view(bronze2, '@dp.table', undefined, 0), highlight: [lineOf(bronze2, "@dp.table(name='globalbank_dev.bronze.card_auths'"), lineOf(bronze2, "@dp.table(name='globalbank_dev.bronze.core_cdc'")] },
  session: s2,
  side: [
    {
      type: 'group', id: 'how', title: deployed2.split(':')[0], sub: deployed2.split(': ').slice(1).join(': '), icon: 'workflow', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'h-code', title: '@dp.table over readStream', sub: 'a streaming table: append-only', icon: 'code' },
        { type: 'item', id: 'h-pipe', title: 'the pipeline runs it', sub: 'serverless; checkpoints are its own', icon: 'databricks' },
        { type: 'item', id: 'h-table', title: 'bronze.card_auths', sub: 'only new files, each update', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'updates', title: `Two updates; ${files2} lines of copy output between`, tone: 'ingest', columns: ['table', 'update 1', 'update 2'],
      rows: r2[0].map((d, i) => ({ id: `u-${i}`, cells: [d.name, fmt(d.rows), fmt(r2[1][i].rows)], tone: 'ingest' as const })),
    },
  ],
  edges: [
    { from: 'h-code', to: 'h-pipe', label: 'deploy' },
    { from: 'h-pipe', to: 'h-table', label: 'update' },
  ],
})

// §3 — materialized views: silver and gold, and how each refresh was computed.
const r3 = runs(s3)
const mv3: SceneModel = ideFrame({
  tree: tree([...PIPES, 'globalbank/deploy.py', 'globalbank/run.py'], 'pipelines/gold.py', ['pipelines/silver.py', 'pipelines/gold.py']),
  editor: { file: 'pipelines/gold.py', code: gold3, highlight: linesFrom(gold3, '@dp.materialized_view', 'GROUP BY ALL') },
  session: s3,
  side: [
    {
      type: 'table', id: 'refresh', title: 'Two updates: what each refresh did', tone: 'consume', columns: ['dataset', 'update 1', 'update 2'],
      rows: r3[1].map((d, i) => ({
        id: `r-${i}`, cells: [d.name, r3[0][i]?.how ?? 'appended', d.how ?? 'appended'], tone: layerTone(d.name),
      })),
    },
    {
      type: 'group', id: 'kinds', title: 'Two kinds of dataset', icon: 'layers', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'k-st', title: 'streaming table', sub: 'appends what is new: bronze', icon: 'stream' },
        { type: 'item', id: 'k-mv', title: 'materialized view', sub: 'a query, kept up to date: silver, gold', icon: 'table' },
        { type: 'item', id: 'k-how', title: 'the refresh decides', sub: 'recompute, or only what changed', icon: 'settings' },
      ],
    },
  ],
  edges: [
    { from: 'k-st', to: 'k-mv', label: 'read by' },
    { from: 'k-mv', to: 'k-how' },
  ],
})

// §4 — the graph: dependencies inferred from reads, drawn from the event log.
const edges4 = all(outputOf(s4, 'python -m globalbank.graph'), /^(\S+)\s+-> (\S+)$/gm).map((m) => ({ from: m[1], to: m[2] }))
const rank = (n: string) => ['bronze', 'silver', 'gold'].indexOf(n.split('.')[0])
const nodes4 = [...new Set(edges4.flatMap((e) => [e.from, e.to]))].sort((a, b) => rank(a) - rank(b))
const graph4Scene: SceneModel = ideFrame({
  tree: tree([...PIPES, 'globalbank/graph.py', 'globalbank/run.py'], 'globalbank/graph.py', ['globalbank/graph.py']),
  editor: { file: 'globalbank/graph.py', code: graph4, highlight: linesFrom(graph4, "SELECT details:flow_definition.output_dataset", "WHERE event_type = 'flow_definition'") },
  session: s4,
  side: [
    {
      type: 'group', id: 'graph', title: 'globalbank_pipeline, as declared', icon: 'workflow', tone: 'store', ...FILL, children:
        nodes4.map((n) => ({ type: 'item' as const, id: nid(n), title: n, sub: n.startsWith('bronze') ? 'streaming table' : 'materialized view', icon: n.startsWith('bronze') ? 'stream' : 'table', tone: layerTone(n) })),
    },
    {
      type: 'table', id: 'edges', title: 'flow_definition events: inputs → output', tone: 'store', columns: ['reads', 'defines'],
      rows: edges4.map((e, i) => ({ id: `e-${i}`, cells: [e.from, e.to] })),
    },
    { type: 'note', id: 'note', tone: 'store', text: 'Nobody wrote this order down: the pipeline read each query, saw which tables it reads, and ran them in that order.' },
  ],
  edges: edges4.map((e) => ({ from: nid(e.from), to: nid(e.to) })),
})

// §5 — expectations: warn and drop, counted by the pipeline.
const q5 = all(outputOf(s5, 'python -m globalbank.quality'), /^(\w+)\s+passed\s+([\d,]+)\s+failed\s+([\d,]+)$/gm).map((m) => ({ name: m[1], passed: num(m[2]), failed: num(m[3]) }))
const policy: Record<string, string> = { currency_known: 'warn: kept', amount_known: 'drop', amount_in_range: 'drop' }
const expect5: SceneModel = ideFrame({
  tree: tree([...PIPES, 'globalbank/quality.py', 'globalbank/run.py'], 'pipelines/silver.py', ['globalbank/quality.py']),
  editor: { file: 'pipelines/silver.py', code: silver5, highlight: linesFrom(silver5, 'RULES = {', "@dp.expect_all_or_drop(RULES)") },
  session: s5,
  side: [
    {
      type: 'table', id: 'q', title: 'Expectations, from the event log', tone: 'consume', columns: ['expectation', 'policy', 'passed', 'failed'],
      rows: q5.map((q) => ({ id: `q-${q.name}`, cells: [q.name, policy[q.name] ?? '', fmt(q.passed), fmt(q.failed)], tone: q.failed ? 'consume' as const : undefined })),
    },
    {
      type: 'table', id: 'policies', title: 'Three policies', tone: 'store', columns: ['decorator', 'a failing row', 'the update'], rows: [
        { id: 'p-warn', cells: ['@dp.expect', 'kept, counted', 'carries on'] },
        { id: 'p-drop', cells: ['@dp.expect_or_drop', 'left out, counted', 'carries on'], tone: 'store' },
        { id: 'p-fail', cells: ['@dp.expect_or_fail', '—', 'stops'] },
      ],
    },
    {
      type: 'group', id: 'flow', title: 'Every row, every update', icon: 'filter', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'e-row', title: 'a bronze row', sub: 'as received', icon: 'layers' },
        { type: 'item', id: 'e-check', title: 'the expectations', sub: 'counted in the event log', icon: 'filter' },
        { type: 'item', id: 'e-silver', title: 'silver, or left out', sub: 'warn keeps it; drop leaves it out', icon: 'check' },
      ],
    },
  ],
  edges: [
    { from: 'e-row', to: 'e-check' },
    { from: 'e-check', to: 'e-silver' },
  ],
})

// §6 — quarantine: the dropped rows, kept; silver reconciled to bronze.
const recon6 = Object.fromEntries(all(outputOf(s6, 'python -m globalbank.recon'), /^(\w+)\s+([\d,]+)$/gm).map((m) => [m[1], num(m[2])]))
const eq6 = outputOf(s6, 'python -m globalbank.recon').split('\n').at(-1)!
const quarantine6: SceneModel = ideFrame({
  tree: tree([...PIPES, 'globalbank/recon.py', 'globalbank/run.py'], 'pipelines/silver.py', ['globalbank/recon.py']),
  editor: { file: 'pipelines/silver.py', code: silver6, ...view(silver6, 'RULES = {', undefined, 0), highlight: linesFrom(silver6, "card_transactions_quarantine')", 'WHERE {broken}') },
  session: s6,
  side: [
    {
      type: 'group', id: 'split', title: 'From one RULES dictionary, two views', icon: 'filter', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'x-bronze', title: `bronze: ${fmt(recon6.bronze)} rows`, sub: 'as received', icon: 'layers' },
        { type: 'item', id: 'x-rules', title: 'RULES', sub: 'silver keeps what passes; quarantine, what fails', icon: 'filter' },
        { type: 'item', id: 'x-both', title: 'two materialized views', sub: 'they can never disagree', icon: 'check' },
      ],
    },
    {
      type: 'table', id: 'ways', title: 'Every bronze row goes one of three ways', tone: 'store', columns: ['to', 'rows', 'why'], rows: [
        { id: 'w-silver', cells: ['silver', fmt(recon6.silver), 'one per auth_id, every rule passed'], tone: 'store' },
        { id: 'w-q', cells: ['quarantine', fmt(recon6.quarantine), 'a rule failed: kept, with the original'], tone: 'consume' },
        { id: 'w-dup', cells: ['resends', fmt(recon6.resends), 'the same auth_id again'] },
      ],
    },
    { type: 'note', id: 'note', tone: 'store', text: `${eq6}: the reconciliation from Course 3, one layer up.` },
  ],
  edges: [
    { from: 'x-bronze', to: 'x-rules' },
    { from: 'x-rules', to: 'x-both' },
  ],
})

// §7 — AUTO CDC: Course 5's MERGE as one declaration.
const r7 = runs(s7)
const cust7 = outputOf(s7, 'python -m globalbank.customer C000001 | tail -1')
const now7 = cust7.match(/silver now: seq (\d+), (.+)$/m)!
const autoCdc7: SceneModel = ideFrame({
  tree: tree([...PIPES, 'globalbank/customer.py', 'globalbank/run.py'], 'pipelines/silver.py'),
  editor: { file: 'pipelines/silver.py', code: silver7, ...view(silver7, '# Course 5', undefined, 0), highlight: linesFrom(silver7, 'dp.create_auto_cdc_flow(', 'stored_as_scd_type=1)') },
  session: s7,
  side: [
    {
      type: 'table', id: 'map', title: 'Course 5’s code, as arguments', tone: 'store', columns: ['Course 5', 'AUTO CDC'], rows: [
        { id: 'm-key', cells: ['ON t.customer_id = s.k', "keys=['customer_id']"] },
        { id: 'm-seq', cells: ['AND s.seq > t.seq', "sequence_by='seq'"], tone: 'store' },
        { id: 'm-del', cells: ["WHEN … s.op = 'D' THEN DELETE", "apply_as_deletes=\"op = 'D'\""] },
        { id: 'm-scd2', cells: ['scd2.py: lead(ts) …', 'stored_as_scd_type=2'], tone: 'store' },
      ],
    },
    {
      type: 'table', id: 'rows', title: `C000001 now: seq ${now7[1]}, ${now7[2]}`, tone: 'ingest', columns: ['table', 'rows'],
      rows: r7[0].filter((d) => d.name.startsWith('silver.customers')).map((d) => ({ id: `t-${d.name}`, cells: [d.name, fmt(d.rows)] })),
    },
    {
      type: 'group', id: 'flow', title: 'Declared, not written', icon: 'workflow', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'c-bronze', title: 'bronze.core_cdc, as a stream', sub: 'every change record', icon: 'stream' },
        { type: 'item', id: 'c-view', title: 'customer_changes', sub: 'a temporary view: after, typed', icon: 'code' },
        { type: 'item', id: 'c-flow', title: 'two AUTO CDC flows', sub: 'customers (type 1), history (type 2)', icon: 'layers' },
      ],
    },
  ],
  edges: [
    { from: 'c-bronze', to: 'c-view' },
    { from: 'c-view', to: 'c-flow', label: 'sequence_by seq' },
  ],
})

// §8 — the event log: every update, every flow, as a table.
const out8 = outputOf(s8, 'python -m globalbank.events')
const kinds8 = all(out8.split('\n')[0], /(\w+) (\d+)/g).map((m) => ({ kind: m[1], n: Number(m[2]) }))
const flows8 = all(out8, /^\s+(\S+)\s+(\w+)\s+(\d+)s$/gm).map((m) => ({ flow: m[1], status: m[2], secs: Number(m[3]) }))
const events8Scene: SceneModel = ideFrame({
  tree: tree([...PIPES, 'globalbank/events.py', 'globalbank/run.py'], 'globalbank/events.py', ['globalbank/events.py']),
  editor: { file: 'globalbank/events.py', code: events8, ...view(events8, 'spark = get_spark()', undefined, 0), highlight: linesFrom(events8, 'SELECT origin.flow_name AS flow', 'GROUP BY ALL HAVING status IS NOT NULL') },
  session: s8,
  side: [
    {
      type: 'plot', id: 'secs', compact: true, title: 'Seconds per flow, running to completed',
      x: { labels: flows8.map((f) => ({ card_auths: 'auths', core_cdc: 'cdc', card_spend_daily: 'spend', card_transactions: 'txns', card_transactions_quarantine: 'quar.', customers: 'cust.', customers_history: 'hist.' } as Record<string, string>)[f.flow.split('.').pop()!] ?? f.flow) }, y: { min: 0, max: Math.ceil(Math.max(...flows8.map((f) => f.secs)) / 20) * 20, step: 20 },
      series: [{ kind: 'bar', points: flows8.map((f, i) => [i, f.secs]), tone: 'store' }],
    },
    {
      type: 'table', id: 'kinds', title: 'The busiest event types', tone: 'store', columns: ['event_type', 'events'],
      rows: kinds8.map((k) => ({ id: `k-${k.kind}`, cells: [k.kind, String(k.n)] })),
    },
  ],
})

// §9 — full refresh: silver and gold rebuild from bronze; bronze is protected.
const counts9 = s9.split(/^\$ /m).slice(1).filter((b) => b.startsWith('python -m globalbank.counts'))
  .map((b) => Object.fromEntries(all(b, /^\s+(\S+)\s+([\d,]+) rows$/gm).map((m) => [m[1], num(m[2])])))
const full9: SceneModel = ideFrame({
  tree: tree([...PIPES, 'globalbank/counts.py', 'globalbank/run.py'], 'pipelines/bronze.py', ['globalbank/counts.py']),
  editor: { file: 'pipelines/bronze.py', code: bronze9, ...view(bronze9, 'KEEP =', undefined, 0), highlight: [lineOf(bronze9, 'KEEP ='), lineOf(bronze9, 'table_properties=KEEP')] },
  session: s9,
  side: [
    {
      type: 'table', id: 'counts', title: 'Rows before and after a full refresh', tone: 'store', columns: ['table', 'before', 'after', 'full refresh'],
      rows: Object.keys(counts9[0]).map((t) => ({
        id: `c-${t}`, cells: [t, fmt(counts9[0][t]), fmt(counts9[1][t]), t.startsWith('bronze') ? 'kept: reset not allowed' : 'rebuilt from bronze'],
        tone: t.startsWith('bronze') ? 'ingest' as const : 'store' as const,
      })),
    },
    {
      type: 'group', id: 'flow', title: 'One full refresh', icon: 'workflow', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'r-start', title: 'run.py --full-refresh', sub: 'recompute every dataset', icon: 'workflow' },
        { type: 'item', id: 'r-bronze', title: 'bronze: reset not allowed', sub: 'kept: files the sources may not send again', icon: 'shield' },
        { type: 'item', id: 'r-rest', title: 'silver and gold: rebuilt', sub: 'from bronze, to the same numbers', icon: 'check' },
      ],
    },
  ],
  edges: [
    { from: 'r-start', to: 'r-bronze' },
    { from: 'r-bronze', to: 'r-rest', label: 'then' },
  ],
})

export const pipelineScenes: Record<string, SceneModel> = {
  'pipeline-why': why1,
  'pipeline-streaming': streaming2,
  'pipeline-mv': mv3,
  'pipeline-graph': graph4Scene,
  'pipeline-expectations': expect5,
  'pipeline-quarantine': quarantine6,
  'pipeline-auto-cdc': autoCdc7,
  'pipeline-event-log': events8Scene,
  'pipeline-full-refresh': full9,
}
