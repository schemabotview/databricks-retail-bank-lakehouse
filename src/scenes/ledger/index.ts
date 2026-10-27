import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import ledger1 from '../../../spine/ledger/01-bad-batch/project/globalbank/ledger.py?raw'
import s1 from '../../../spine/ledger/01-bad-batch/session.txt?raw'
import daily2 from '../../../spine/ledger/02-time-travel/project/globalbank/daily.py?raw'
import s2 from '../../../spine/ledger/02-time-travel/session.txt?raw'
import restore3 from '../../../spine/ledger/03-restore/project/globalbank/restore.py?raw'
import s3 from '../../../spine/ledger/03-restore/session.txt?raw'
import ledger4 from '../../../spine/ledger/04-constraints/project/globalbank/ledger.py?raw'
import s4 from '../../../spine/ledger/04-constraints/session.txt?raw'
import writers5 from '../../../spine/ledger/05-two-writers/project/globalbank/writers.py?raw'
import s5 from '../../../spine/ledger/05-two-writers/session.txt?raw'
import ledger6 from '../../../spine/ledger/06-settle/project/globalbank/ledger.py?raw'
import s6 from '../../../spine/ledger/06-settle/session.txt?raw'
import dv7 from '../../../spine/ledger/07-deletion-vectors/project/globalbank/dv.py?raw'
import s7 from '../../../spine/ledger/07-deletion-vectors/session.txt?raw'
import ledger8 from '../../../spine/ledger/08-change-feed/project/globalbank/ledger.py?raw'
import changes8 from '../../../spine/ledger/08-change-feed/project/globalbank/changes.py?raw'
import s8 from '../../../spine/ledger/08-change-feed/session.txt?raw'

// Course 4 — Make the ledger trustworthy (bronze → silver). Every frame is a workspace run
// (spine/ledger/), replayed on the owner's Free Edition workspace; every number is read from a session.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const num = (s: string) => Number(s.replace(/,/g, ''))
const fmt = (n: number) => n.toLocaleString('en')
const FILL = { spread: true, minH: 520 } as const
const SILVER = 'globalbank_dev.silver.card_transactions'
const PKG = ['globalbank/__init__.py', 'globalbank/session.py', 'globalbank/land.py']
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...PKG, ...files, 'globalbank_sim/', 'land.sh'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const days = (out: string) => all(out, /^(\d{4}-\d{2}-(\d{2}))\s+([\d,]+) auths\s+([\d,.]+) EUR$/gm)
  .map((m) => ({ day: m[1], dd: m[2], auths: num(m[3]), spend: num(m[4]) }))
const versions = (out: string) => all(out, /^version (\d+)\s+(\S+(?: \S+)?)\s*(\d*)$/gm)
  .map((m) => ({ v: Number(m[1]), op: m[2].trim(), rows: m[3] }))
const rowsOf = (out: string) => num(out.match(/: ([\d,]+) rows/)![1])
const HISTORY = `python -m globalbank.history ${SILVER}`
const spendPlot = (id: string, title: string, ds: ReturnType<typeof days>) => {
  const top = Math.ceil(Math.max(...ds.map((d) => d.spend)) / 200000) * 200000
  return {
    type: 'plot' as const, id, compact: true, title,
    x: { labels: ds.map((d) => `${Number(d.dd)} Oct`) }, y: { min: 0, max: top, step: top / 4 },
    series: [{ kind: 'bar' as const, points: ds.map((d, i) => [i, d.spend] as [number, number]), tone: 'consume' as const }],
  }
}

// §1 — a bad batch lands: the 14 October file in cents, posted to silver.
const posted1 = rowsOf(outputOf(s1, 'python -m globalbank.ledger post 2026-10-14'))
const d1 = days(outputOf(s1, 'python -m globalbank.daily'))
const bad = d1.at(-1)!
const usual = d1.slice(0, -1)
const avg = usual.reduce((a, d) => a + d.spend, 0) / usual.length
const badBatch1: SceneModel = ideFrame({
  tree: tree(['globalbank/daily.py', 'globalbank/ledger.py'], 'globalbank/ledger.py', ['globalbank/ledger.py', 'globalbank/daily.py']),
  editor: { file: 'globalbank/ledger.py', code: ledger1, ...view(ledger1, 'def post', undefined, 0), highlight: linesFrom(ledger1, 'MERGE INTO', 'ON t.auth_id') },
  session: s1,
  side: [
    spendPlot('spend', 'Approved card spend per day, EUR', d1),
    {
      type: 'table', id: 'days', title: `silver: ${fmt(posted1)} rows, five days posted`, tone: 'consume', columns: ['day', 'auths', 'spend, EUR'],
      rows: d1.map((d) => ({ id: `d-${d.dd}`, cells: [d.day, fmt(d.auths), fmt(d.spend)], tone: d === bad ? 'consume' as const : undefined })),
    },
    { type: 'note', id: 'note', tone: 'consume', text: `14 October: fewer authorizations than any other day, and ${(bad.spend / avg).toFixed(1)}× the usual spend. One file arrived in cents.` },
  ],
})

// §2 — time travel: the table's versions, and the totals as of the version before the batch.
const v2 = versions(outputOf(s2, HISTORY))
const badV = v2.at(-1)!.v
const d2 = days(outputOf(s2, `python -m globalbank.daily ${badV - 1}`))
const timeTravel2: SceneModel = ideFrame({
  tree: tree(['globalbank/daily.py', 'globalbank/history.py', 'globalbank/ledger.py'], 'globalbank/daily.py', ['globalbank/history.py']),
  editor: { file: 'globalbank/daily.py', code: daily2, highlight: [lineOf(daily2, 'VERSION AS OF'), lineOf(daily2, '{SILVER}{version}')] },
  session: s2,
  side: [
    {
      type: 'table', id: 'versions', title: `DESCRIBE HISTORY: ${v2.length} versions`, tone: 'infra', columns: ['version', 'operation', 'rows', 'what'],
      rows: v2.map((r) => ({
        id: `v-${r.v}`, cells: [String(r.v), r.op, r.rows ? fmt(Number(r.rows)) : '', r.v === 0 ? 'the empty table' : r.v === badV ? '14 Oct: the bad batch' : `${9 + r.v} Oct posted`],
        tone: r.v === badV - 1 ? 'ingest' as const : r.v === badV ? 'consume' as const : undefined,
      })),
    },
    spendPlot('asof', `Spend per day, VERSION AS OF ${badV - 1}`, d2),
    { type: 'note', id: 'note', tone: 'ingest', text: `Every commit is a version, and every version can still be read. Version ${badV - 1} is the ledger the evening before the batch.` },
  ],
})

// §3 — RESTORE: back to the version before; the restore is itself a version.
const restored = outputOf(s3, `python -m globalbank.restore ${SILVER} ${badV - 1}`)
const [, removed3, restoredN] = restored.match(/removed (\d+) file\(s\), restored (\d+)/)!
const v3 = versions(outputOf(s3, `${HISTORY} | tail -2`))
const d3 = days(outputOf(s3, 'python -m globalbank.daily'))
const restore3Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/daily.py', 'globalbank/history.py', 'globalbank/ledger.py', 'globalbank/restore.py'], 'globalbank/restore.py', ['globalbank/restore.py']),
  editor: { file: 'globalbank/restore.py', code: restore3, highlight: [lineOf(restore3, 'RESTORE TABLE')] },
  session: s3,
  side: [
    {
      type: 'group', id: 'line', title: 'History only grows', icon: 'clock', tone: 'infra', ...FILL, children: [
        { type: 'item', id: 'h-good', title: `version ${badV - 1}: MERGE`, sub: '13 October posted: correct', icon: 'check' },
        { type: 'item', id: 'h-bad', title: `version ${v3[0].v}: ${v3[0].op}`, sub: '14 October, in cents', icon: 'bell' },
        { type: 'item', id: 'h-restore', title: `version ${v3[1].v}: ${v3[1].op}`, sub: `the table as of version ${badV - 1}`, icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'after', title: 'Spend per day, now', tone: 'ingest', columns: ['day', 'spend, EUR'],
      rows: d3.map((d) => ({ id: `a-${d.dd}`, cells: [d.day, fmt(d.spend)] })),
    },
    { type: 'note', id: 'note', tone: 'infra', text: `RESTORE removed ${removed3} file(s) from the table and restored ${restoredN}: the bad MERGE had only added a file. Version ${v3[0].v} can still be read, for whoever has to explain what happened.` },
  ],
  edges: [
    { from: 'h-good', to: 'h-bad', label: 'post' },
    { from: 'h-bad', to: 'h-restore', label: 'restore' },
  ],
})

// §4 — constraints: the same file again is refused, and the table does not change.
const refused4 = outputOf(s4, 'python -m globalbank.ledger post 2026-10-14').split('\n')
const reason4 = refused4[0].replace('refused: ', '')
const v4 = versions(outputOf(s4, `${HISTORY} | tail -3`))
const constraints4: SceneModel = ideFrame({
  tree: tree(['globalbank/daily.py', 'globalbank/history.py', 'globalbank/ledger.py', 'globalbank/restore.py'], 'globalbank/ledger.py'),
  editor: { file: 'globalbank/ledger.py', code: ledger4, ...view(ledger4, 'def create', 'def post', 0), highlight: linesFrom(ledger4, 'ADD CONSTRAINT', 'CHECK (amount') },
  session: s4,
  side: [
    {
      type: 'group', id: 'path', title: 'The 14 October file, posted again', icon: 'shield', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'c-write', title: 'MERGE: 14 October', sub: 'amounts ×100, up to five figures', icon: 'card' },
        { type: 'item', id: 'c-check', title: 'CHECK (amount > 0 AND amount <= 1000)', sub: 'checked on every row of every write', icon: 'filter' },
        { type: 'item', id: 'c-no', title: reason4.replace(/_/g, '_\u200b'), sub: `first value: ${refused4[1].replace(/^- amount : /, '').replace(/\.$/, '')}; the whole write is refused`, icon: 'bell' },
      ],
    },
    {
      type: 'table', id: 'hist', title: 'The last versions: the refused write made none', tone: 'infra', columns: ['version', 'operation'],
      rows: v4.map((r) => ({ id: `h-${r.v}`, cells: [String(r.v), r.op], tone: r === v4.at(-1) ? 'ingest' as const : undefined })),
    },
    { type: 'note', id: 'note', tone: 'consume', text: 'The limit is illustrative, not a real card rule. Course 7 turns rules like it into expectations that quarantine rows instead of refusing a whole file.' },
  ],
  edges: [
    { from: 'c-write', to: 'c-check' },
    { from: 'c-check', to: 'c-no', label: 'a row fails' },
  ],
})

// §5 — two writers, one table: two days posted at the same moment.
const out5 = outputOf(s5, 'python -m globalbank.writers 2026-10-15 2026-10-16')
const committed5 = all(out5, /^(\S+): committed on attempt (\d+)$/gm).map((m) => ({ day: m[1], attempt: Number(m[2]) }))
const conflict5 = out5.match(/^\S+: (DELTA_\w+), retrying$/m)?.[1] ?? ''
const v5 = versions(outputOf(s5, `${HISTORY} | tail -3`))
const writers5Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/history.py', 'globalbank/ledger.py', 'globalbank/writers.py'], 'globalbank/writers.py', ['globalbank/writers.py']),
  editor: { file: 'globalbank/writers.py', code: writers5, ...view(writers5, 'def post_until_committed', undefined, 0), highlight: linesFrom(writers5, 'except Exception as e:', "print(f'{day}: {conflict.group(1)}, retrying')") },
  session: s5,
  side: [
    {
      type: 'group', id: 'log', title: 'One table, one log', icon: 'layers', tone: 'infra', ...FILL, children: [
        { type: 'item', id: 'w-a', title: 'both MERGEs read the same version', sub: 'and write their new files, unseen', icon: 'workflow' },
        { type: 'item', id: 'w-log', title: '_delta_log: one commit wins', sub: 'the next version number goes to the first', icon: 'file' },
        { type: 'item', id: 'w-b', title: `the other: ${conflict5}`, sub: `it read the whole table, now changed: retried, attempt ${Math.max(...committed5.map((c) => c.attempt))}`, icon: 'bell' },
      ],
    },
    {
      type: 'table', id: 'hist', title: 'Two commits, two versions', tone: 'infra', columns: ['version', 'operation', 'rows'],
      rows: v5.map((r) => ({ id: `h-${r.v}`, cells: [String(r.v), r.op, r.rows ? fmt(Number(r.rows)) : ''], tone: r.op === 'MERGE' ? 'ingest' as const : undefined })),
    },
  ],
  edges: [
    { from: 'w-a', to: 'w-log', label: 'commit' },
    { from: 'w-log', to: 'w-b', label: 'conflict' },
  ],
})

// §6 — settling: MERGE the clearing file, AUTHORIZED → SETTLED / REVERSED.
const landed6 = outputOf(s6, 'python -m globalbank.land settlements')
const st6 = all(outputOf(s6, 'python -m globalbank.statuses'), /^(\w+)\s+([\d,]+) auths(?:\s+([\d,.]+) EUR)?$/gm)
  .map((m) => ({ status: m[1], auths: num(m[2]), eur: m[3] }))
const clearing6 = num(landed6.match(/= ([\d,]+) rows/)![1])
const settle6: SceneModel = ideFrame({
  tree: tree(['globalbank/ledger.py', 'globalbank/statuses.py'], 'globalbank/ledger.py', ['globalbank/statuses.py']),
  editor: { file: 'globalbank/ledger.py', code: ledger6, ...view(ledger6, 'def settle', undefined, 0), highlight: linesFrom(ledger6, 'WHEN MATCHED THEN UPDATE', 'cleared_date = s.cleared_date') },
  session: s6,
  side: [
    {
      type: 'group', id: 'paths', title: 'MERGE, one clearing row at a time', icon: 'workflow', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'm-row', title: `clearing file, 11 October: ${fmt(clearing6)} rows`, sub: 'auth_id, kind, amount_eur', icon: 'file' },
        { type: 'item', id: 'm-on', title: 'ON t.auth_id = s.auth_id', sub: 'find the authorization it clears', icon: 'search' },
        { type: 'item', id: 'm-match', title: 'matched: SETTLED or REVERSED', sub: 'not matched: authorized before 10 October, skipped', icon: 'check' },
      ],
    },
    {
      type: 'table', id: 'status', title: 'Silver by status, after one clearing file', tone: 'ingest', columns: ['status', 'auths', 'settled, EUR'],
      rows: st6.map((r) => ({ id: `s-${r.status}`, cells: [r.status, fmt(r.auths), r.eur ?? ''], tone: r.eur ? 'ingest' as const : undefined })),
    },
    { type: 'note', id: 'note', tone: 'source', text: `The scheme’s clearing file for 11 October, one CSV, became bronze.settlements through the same Auto Loader code as the cards: ${fmt(clearing6)} rows.` },
  ],
  edges: [
    { from: 'm-row', to: 'm-on' },
    { from: 'm-on', to: 'm-match', label: 'WHEN MATCHED' },
  ],
})

// §7 — deletion vectors: the MERGE marks rows instead of rewriting files.
const out7 = outputOf(s7, 'python -m globalbank.dv')
const metric = (k: string) => out7.match(new RegExp(`${k}\\s+(\\S+)`))![1]
const dvOn7 = /^deletionVectors: on/m.test(out7)
const dv7Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/dv.py', 'globalbank/ledger.py'], 'globalbank/dv.py', ['globalbank/dv.py']),
  editor: { file: 'globalbank/dv.py', code: dv7, highlight: linesFrom(dv7, "for key in ['numTargetRowsUpdated'", "'numTargetDeletionVectorsAdded'") },
  session: s7,
  side: [
    {
      type: 'group', id: 'file', title: 'Updating rows without rewriting a file', icon: 'file', tone: 'infra', ...FILL, children: [
        { type: 'item', id: 'f-old', title: 'the data file', sub: 'thousands of rows, unchanged on disk', icon: 'layers' },
        { type: 'item', id: 'f-dv', title: 'its deletion vector', sub: 'a bitmap: these rows are replaced', icon: 'filter' },
        { type: 'item', id: 'f-new', title: 'a small new file', sub: 'only the updated rows, written again', icon: 'file' },
      ],
    },
    {
      type: 'table', id: 'metrics', title: 'What the last MERGE did', tone: 'infra', columns: ['metric', 'value'], rows: [
        { id: 'k-upd', cells: ['rows updated', metric('numTargetRowsUpdated')] },
        { id: 'k-add', cells: ['files added', metric('numTargetFilesAdded')] },
        { id: 'k-rem', cells: ['files removed', metric('numTargetFilesRemoved')], tone: 'ingest' },
        { id: 'k-dv', cells: ['deletion vectors added', metric('numTargetDeletionVectorsAdded')], tone: 'ingest' },
        { id: 'k-feat', cells: ['deletionVectors feature', dvOn7 ? 'on' : 'off'] },
      ],
    },
  ],
  edges: [
    { from: 'f-old', to: 'f-dv', label: 'marks' },
    { from: 'f-dv', to: 'f-new', label: 'replaced by' },
  ],
})

// §8 — the change data feed: what the last version did, row by row.
const out8 = outputOf(s8, 'python -m globalbank.changes')
const head8 = out8.split('\n')[0]
const counts8 = Object.fromEntries(all(head8.split(': ')[1], /(\w+) ([\d,]+)/g).map((m) => [m[1], num(m[2])]))
const rows8 = all(out8, /^\s+(au-\S+)\s+(\S+)\s+(\S+)\s+(\S+)$/gm).map((m) => m.slice(1, 5))
const feed8: SceneModel = ideFrame({
  tree: tree(['globalbank/changes.py', 'globalbank/ledger.py'], 'globalbank/changes.py', ['globalbank/changes.py']),
  editor: { file: 'globalbank/changes.py', code: changes8, highlight: [lineOf(changes8, 'table_changes')] },
  session: s8,
  side: [
    {
      type: 'table', id: 'kinds', title: `${head8.split(':')[0]}: the feed, counted`, tone: 'ingest', columns: ['_change_type', 'rows'],
      rows: Object.entries(counts8).map(([k, n]) => ({ id: `k-${k}`, cells: [k, fmt(n)], tone: k.startsWith('update') ? 'ingest' as const : undefined })),
    },
    {
      type: 'table', id: 'rows', title: 'One update is two rows: before and after', tone: 'ingest', columns: ['auth_id', '_change_type', 'status', 'settled_eur'],
      rows: rows8.map((r, i) => ({ id: `r-${i}`, cells: r, tone: r[1] === 'update_postimage' ? 'ingest' as const : undefined })),
    },
    { type: 'note', id: 'note', tone: 'ingest', text: `One table property, delta.enableChangeDataFeed (line ${lineOf(ledger8, 'enableChangeDataFeed')} of ledger.py), and every later version can be read as the rows it changed: what a downstream reader applies, instead of the whole table.` },
  ],
})

export const ledgerScenes: Record<string, SceneModel> = {
  'ledger-bad-batch': badBatch1,
  'ledger-time-travel': timeTravel2,
  'ledger-restore': restore3Scene,
  'ledger-constraints': constraints4,
  'ledger-writers': writers5Scene,
  'ledger-settle': settle6,
  'ledger-dv': dv7Scene,
  'ledger-feed': feed8,
}
