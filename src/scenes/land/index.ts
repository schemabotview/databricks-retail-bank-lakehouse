import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import reread from '../../../spine/land/01-reread/project/globalbank/reread.py?raw'
import s1 from '../../../spine/land/01-reread/session.txt?raw'
import land2 from '../../../spine/land/02-auto-loader/project/globalbank/land.py?raw'
import s2 from '../../../spine/land/02-auto-loader/session.txt?raw'
import s3 from '../../../spine/land/03-checkpoint/session.txt?raw'
import land4 from '../../../spine/land/04-schema-hints/project/globalbank/land.py?raw'
import s4 from '../../../spine/land/04-schema-hints/session.txt?raw'
import land5 from '../../../spine/land/05-schema-evolution/project/globalbank/land.py?raw'
import s5 from '../../../spine/land/05-schema-evolution/session.txt?raw'
import rescued6 from '../../../spine/land/06-rescued-data/project/globalbank/rescued.py?raw'
import s6 from '../../../spine/land/06-rescued-data/session.txt?raw'
import land7 from '../../../spine/land/07-file-metadata/project/globalbank/land.py?raw'
import s7 from '../../../spine/land/07-file-metadata/session.txt?raw'
import reconcile8 from '../../../spine/land/08-reconcile/project/globalbank/reconcile.py?raw'
import s8 from '../../../spine/land/08-reconcile/session.txt?raw'

// Course 3 — Land the card stream (landing → bronze). Every frame is a workspace run
// (spine/land/), replayed on the owner's Free Edition workspace; every number is read from a session.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const num = (s: string) => Number(s.replace(/,/g, ''))
const FILL = { spread: true, minH: 520 } as const  // with the side pane's own spread (ide.ts)
const PKG = ['globalbank/__init__.py', 'globalbank/session.py', 'globalbank/catalog.py']
const TOP = ['.venv/', 'landing/']
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: [...TOP, ...PKG, ...files, 'globalbank_sim/', 'land.sh'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const TABLE = 'globalbank_dev.bronze.card_auths'
const COLS = `python -m globalbank.columns ${TABLE}`
const types = (out: string) => all(out, /(\S+) (\S+)(?:\s{2}|$)/g).map((m) => [m[1], m[2]])
const runs = (session: string) => all(session, /: ([\d,]+) \+ ([\d,]+) = ([\d,]+) rows/g).map((m) => ({ before: num(m[1]), added: num(m[2]), after: num(m[3]) }))

// §1 — files keep arriving: the naive job re-reads all of them.
const reads = all(s1, /^read ([\d,]+) rows from (\d+) files$/gm).map((m) => ({ rows: num(m[1]), files: Number(m[2]) }))
const fresh = reads.map((r, i) => r.rows - (i ? reads[i - 1].rows : 0))
const peak = Math.ceil(reads.at(-1)!.rows / 5000) * 5000
const reread1: SceneModel = ideFrame({
  tree: tree(['globalbank/reread.py'], 'globalbank/reread.py', ['globalbank/reread.py']),
  editor: { file: 'globalbank/reread.py', code: reread, highlight: [lineOf(reread, 'spark.read.json')] },
  session: s1,
  side: [
    {
      type: 'plot', id: 'reads', compact: true, title: 'Rows per run: read (left), new (right)',
      x: { labels: reads.map((_, i) => (i ? `to ${i + 1} Oct` : '1 Oct')) }, y: { min: 0, max: peak, step: peak / 4 },
      series: [
        { kind: 'bar', points: reads.map((r, i) => [i, r.rows]), label: 'read', tone: 'consume' },
        { kind: 'bar', points: fresh.map((n, i) => [i, n]), label: 'new', tone: 'store' },
      ],
    },
    {
      type: 'table', id: 'cost', title: 'Every run reads every file again', tone: 'consume', columns: ['run', 'files read', 'rows read', 'new'],
      rows: reads.map((r, i) => ({ id: `r${i}`, cells: [String(i + 1), String(r.files), r.rows.toLocaleString('en'), fresh[i].toLocaleString('en')] })),
    },
    { type: 'note', id: 'note', tone: 'consume', text: 'Two months of files would mean reading two months on every run, and nothing stops the same row from being written twice.' },
  ],
})

// §2 — Auto Loader: cloudFiles + availableNow writes only what is new.
const r2 = runs(s2)
const cols2 = types(outputOf(s2, COLS))
const autoLoader2: SceneModel = ideFrame({
  tree: tree(['globalbank/columns.py', 'globalbank/land.py', 'globalbank/reread.py'], 'globalbank/land.py', ['globalbank/land.py', 'globalbank/columns.py']),
  editor: { file: 'globalbank/land.py', code: land2, ...view(land2, 'def ingest', 'query.awaitTermination()', 0),
    highlight: [lineOf(land2, "format('cloudFiles')"), lineOf(land2, 'availableNow=True')] },
  session: s2,
  side: [
    {
      type: 'group', id: 'flow', title: 'One run of ingest()', icon: 'stream', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'f-files', title: 'the volume', sub: 'card_auths/<day>/auths-<hhmm>.json', icon: 'folder' },
        { type: 'item', id: 'f-al', title: 'Auto Loader (cloudFiles)', sub: 'lists the folder, skips what it has seen', icon: 'search' },
        { type: 'item', id: 'f-table', title: 'bronze.card_auths', sub: 'appends only the new files’ rows', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'runs', title: 'Two runs', tone: 'ingest', columns: ['run', 'before', 'added', 'after'],
      rows: r2.map((r, i) => ({ id: `run${i}`, cells: [String(i + 1), r.before.toLocaleString('en'), `+ ${r.added.toLocaleString('en')}`, r.after.toLocaleString('en')], tone: 'ingest' as const })),
    },
    {
      type: 'table', id: 'types', title: 'What it inferred', tone: 'consume', columns: ['column', 'type'],
      rows: cols2.filter(([c]) => ['amount', 'auth_ts', '_rescued_data'].includes(c)).map(([c, t]) => ({ id: `t-${c}`, cells: [c, t], tone: c === '_rescued_data' ? undefined : 'consume' as const })),
    },
  ],
  edges: [
    { from: 'f-files', to: 'f-al', label: 'new files' },
    { from: 'f-al', to: 'f-table', label: 'append' },
  ],
})

// §3 — the checkpoint: what makes "only new" true. (A lab: no code changes.)
const r3 = runs(s3)
const ckpt = outputOf(s3, 'databricks fs ls dbfs:/Volumes/globalbank_dev/bronze/checkpoints/card_auths').split('\n').filter(Boolean)
const meaning: Record<string, string> = {
  _schemas: 'the schema Auto Loader inferred, by version', commits: 'each finished batch', metadata: 'the stream’s id',
  offsets: 'what each batch was about to read', sources: 'every file already seen',
}
const checkpoint3: SceneModel = ideFrame({
  tree: tree(['globalbank/columns.py', 'globalbank/land.py'], 'globalbank/land.py'),
  editor: { file: 'globalbank/land.py', code: land2, ...view(land2, 'CHECKPOINT =', 'query.awaitTermination()', 0),
    highlight: [lineOf(land2, 'CHECKPOINT ='), lineOf(land2, ".option('checkpointLocation'")] },
  session: s3,
  side: [
    {
      type: 'table', id: 'folders', title: '/Volumes/…/checkpoints/card_auths', tone: 'ingest', columns: ['folder', 'remembers'],
      rows: ckpt.map((f) => ({ id: `c-${f}`, cells: [f, meaning[f] ?? ''], tone: f === 'sources' ? 'ingest' as const : undefined })),
    },
    {
      type: 'plot', id: 'rows', compact: true, title: 'Rows in bronze after each run',
      x: { labels: ['run again', 'checkpoint deleted'] }, y: { min: 0, max: Math.ceil(r3[1].after / 5000) * 5000, step: 5000 },
      series: [{ kind: 'bar', points: [[0, r3[0].after], [1, r3[1].after]], tone: 'consume' }],
    },
    { type: 'note', id: 'note', tone: 'consume', text: `Without its checkpoint the stream forgot every file and appended all ${r3[1].added.toLocaleString('en')} rows again: bronze now holds each one twice.` },
  ],
})

// §4 — schema hints: the two columns a bank cannot leave as strings.
const cols4 = types(outputOf(s4, COLS))
const hint = (c: string) => cols4.find(([n]) => n === c)![1]
const was = (c: string) => cols2.find(([n]) => n === c)![1]
const hints4: SceneModel = ideFrame({
  tree: tree(['globalbank/columns.py', 'globalbank/land.py'], 'globalbank/land.py'),
  editor: { file: 'globalbank/land.py', code: land4, ...view(land4, 'HINTS =', 'query.awaitTermination()', 0),
    highlight: [lineOf(land4, 'HINTS ='), lineOf(land4, 'schemaHints')] },
  session: s4,
  side: [
    {
      type: 'table', id: 'types', title: 'Inferred (2.2) against hinted (this run)', tone: 'ingest', columns: ['column', 'inferred', 'hinted'],
      rows: ['amount', 'auth_ts', 'card_id', 'status'].map((c) => ({
        id: `h-${c}`, cells: [c, was(c), hint(c)], tone: was(c) !== hint(c) ? 'ingest' as const : undefined,
      })),
    },
    {
      type: 'group', id: 'why', title: 'Why JSON reads as strings', icon: 'file', tone: 'source', ...FILL, children: [
        { type: 'item', id: 'w-json', title: '"amount": 57.72', sub: 'JSON has numbers, but no decimals', icon: 'code' },
        { type: 'item', id: 'w-al', title: 'Auto Loader: strings by default', sub: 'safe: no value is ever lost to a wrong type', icon: 'shield' },
        { type: 'item', id: 'w-hint', title: 'a hint for what we know', sub: 'money exact to the cent; times as timestamps', icon: 'check' },
      ],
    },
  ],
  edges: [
    { from: 'w-json', to: 'w-al' },
    { from: 'w-al', to: 'w-hint' },
  ],
})

// §5 — schema evolution: 15 October adds wallet_type; the stream stops, then carries on.
const stopped = s5.match(/stream stopped: (\S+)/)![1]
const newCol = s5.match(/new column: (.+)$/m)![1]
const r5 = runs(s5)
const files5 = outputOf(s5, 'bash land.sh 2026-10-15 | wc -l').trim()
const evolve5: SceneModel = ideFrame({
  tree: tree(['globalbank/columns.py', 'globalbank/land.py'], 'globalbank/land.py'),
  editor: { file: 'globalbank/land.py', code: land5, ...view(land5, 'def ingest', "print('new column:'", 0),
    highlight: [lineOf(land5, "option('mergeSchema'"), ...linesFrom(land5, 'except StreamingQueryException', 'raise SystemExit(1)')] },
  session: s5,
  side: [
    {
      type: 'group', id: 'runs', title: 'The same command, twice', icon: 'stream', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'e-land', title: `15 October: ${files5} files`, sub: 'the processor added wallet_type', icon: 'card' },
        { type: 'item', id: 'e-stop', title: 'run 1: the stream stops', sub: `${stopped.split('.')[0]}: schema updated to add ${newCol.split(' ')[0]}`, icon: 'bell' },
        { type: 'item', id: 'e-go', title: `run 2: + ${r5[0].added.toLocaleString('en')} rows`, sub: 'restarts with the new column', icon: 'check' },
      ],
    },
    {
      type: 'table', id: 'schema', title: 'The schema, by version', tone: 'ingest', columns: ['version', 'columns'], rows: [
        { id: 'v1', cells: ['before', '9 + _rescued_data'] },
        { id: 'v2', cells: ['after', `+ ${newCol.toLowerCase()}`], tone: 'ingest' },
      ],
    },
  ],
  edges: [
    { from: 'e-land', to: 'e-stop' },
    { from: 'e-stop', to: 'e-go', label: 'run again' },
  ],
})

// §6 — rescued data: "12,50" does not fit DECIMAL(18,2), so it is kept aside, not lost.
const rows6 = all(outputOf(s6, 'python -m globalbank.rescued'), /^\|(au-\S+)\|\s*(\S+)\|\s*(\S+)\|$/gm).map((m) => [m[1], m[2], m[3]])
const rescued6Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/columns.py', 'globalbank/land.py', 'globalbank/rescued.py'], 'globalbank/rescued.py', ['globalbank/rescued.py']),
  editor: { file: 'globalbank/rescued.py', code: rescued6, highlight: linesFrom(rescued6, ".where(F.col('_rescued_data')", "F.get_json_object") },
  session: s6,
  side: [
    {
      type: 'group', id: 'path', title: 'One partner row', icon: 'card', tone: 'source', ...FILL, children: [
        { type: 'item', id: 'p-in', title: `"amount": "${rows6[0][2]}"`, sub: 'a string, with a comma', icon: 'file' },
        { type: 'item', id: 'p-hint', title: 'amount DECIMAL(18,2)', sub: 'the hint cannot parse it', icon: 'filter' },
        { type: 'item', id: 'p-row', title: 'the row is kept', sub: 'amount NULL; the original in _rescued_data', icon: 'shield' },
      ],
    },
    {
      type: 'table', id: 'rows', title: `${rows6.length} rows rescued`, tone: 'consume', columns: ['auth_id', 'amount', 'rescued'],
      rows: rows6.map(([id, amount, value]) => ({ id: `x-${id}`, cells: [id, amount, value], tone: 'consume' as const })),
    },
  ],
  edges: [
    { from: 'p-in', to: 'p-hint' },
    { from: 'p-hint', to: 'p-row' },
  ],
})

// §7 — where each row came from: the file and the time it landed.
const top7 = all(outputOf(s7, 'python -m globalbank.sources'), /^\|(auths-\S+)\s*\|(\S+ \S+)\|(\d+)\s*\|$/gm).map((m) => [m[1], m[2], m[3]])
const metadata7: SceneModel = ideFrame({
  tree: tree(['globalbank/columns.py', 'globalbank/land.py', 'globalbank/rescued.py', 'globalbank/sources.py'], 'globalbank/land.py', ['globalbank/sources.py']),
  editor: { file: 'globalbank/land.py', code: land7, ...view(land7, 'def ingest', 'query.awaitTermination()', 0),
    highlight: linesFrom(land7, ".withColumn('source_file'", "F.col('_metadata.file_modification_time')") },
  session: s7,
  side: [
    {
      type: 'table', id: 'meta', title: 'Two columns bronze adds to every row', tone: 'ingest', columns: ['column', 'from', 'answers'], rows: [
        { id: 'm-file', cells: ['source_file', '_metadata.file_path', 'which file?'], tone: 'ingest' },
        { id: 'm-time', cells: ['landed_at', '_metadata.file_modification_time', 'when did it arrive?'], tone: 'ingest' },
      ],
    },
    {
      type: 'table', id: 'busiest', title: 'The busiest files of 1 October', tone: 'source', columns: ['file', 'rows'],
      rows: top7.map(([f, , n]) => ({ id: `b-${f}`, cells: [f, n] })),
    },
    { type: 'note', id: 'note', tone: 'ingest', text: 'Bronze’s promise is complete, and complete includes provenance: any row can be traced to the exact file it came from, and that file is still in the volume.' },
  ],
})

// §8 — bronze, reconciled: the volume and the table agree, line for line.
const recon = Object.fromEntries(all(outputOf(s8, 'python -m globalbank.reconcile'), /^(.+?)\s{2,}([\d,]+)$/gm).map((m) => [m[1], num(m[2])]))
const reconcile8Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/land.py', 'globalbank/reconcile.py', 'globalbank/sources.py'], 'globalbank/reconcile.py', ['globalbank/reconcile.py']),
  editor: { file: 'globalbank/reconcile.py', code: reconcile8, ...view(reconcile8, 'SOURCE =', undefined, 0), highlight: linesFrom(reconcile8, 'counts = {', '}') },
  session: s8,
  side: [
    {
      type: 'group', id: 'eq', title: 'Three days, three checks', icon: 'check', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'q-files', title: `${recon['files in the volume']} files = ${recon['files in bronze']} files`, sub: 'every file landed was ingested', icon: 'folder' },
        { type: 'item', id: 'q-lines', title: `${recon['lines in the files'].toLocaleString('en')} lines = ${recon['rows in bronze'].toLocaleString('en')} rows`, sub: 'every line is a row', icon: 'table' },
        { type: 'item', id: 'q-ids', title: `${recon['rows in bronze'].toLocaleString('en')} = ${recon['distinct auth_id'].toLocaleString('en')} + ${recon['sent twice']}`, sub: 'authorizations + resends, kept as received', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'next', title: 'What bronze keeps, and who fixes it', tone: 'store', columns: ['in bronze', 'fixed in'], rows: [
        { id: 'n-resend', cells: [`${recon['sent twice']} resends`, 'silver: one row per auth_id (4)'] },
        { id: 'n-rescued', cells: ['rescued rows', 'silver: quarantined (7)'] },
      ],
    },
  ],
  edges: [
    { from: 'q-files', to: 'q-lines' },
    { from: 'q-lines', to: 'q-ids' },
  ],
})

export const landScenes: Record<string, SceneModel> = {
  'land-reread': reread1,
  'land-auto-loader': autoLoader2,
  'land-checkpoint': checkpoint3,
  'land-hints': hints4,
  'land-evolution': evolve5,
  'land-rescued': rescued6Scene,
  'land-metadata': metadata7,
  'land-reconcile': reconcile8Scene,
}
