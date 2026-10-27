import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import record1 from '../../../spine/customers/01-change-records/project/globalbank/record.py?raw'
import s1 from '../../../spine/customers/01-change-records/session.txt?raw'
import cdc2 from '../../../spine/customers/02-current-state/project/globalbank/cdc.py?raw'
import s2 from '../../../spine/customers/02-current-state/session.txt?raw'
import customer3 from '../../../spine/customers/03-out-of-order/project/globalbank/customer.py?raw'
import s3 from '../../../spine/customers/03-out-of-order/session.txt?raw'
import cdc4 from '../../../spine/customers/04-in-sequence/project/globalbank/cdc.py?raw'
import s4 from '../../../spine/customers/04-in-sequence/session.txt?raw'
import cdc5 from '../../../spine/customers/05-deletes/project/globalbank/cdc.py?raw'
import s5 from '../../../spine/customers/05-deletes/session.txt?raw'
import scd6 from '../../../spine/customers/06-history/project/globalbank/scd2.py?raw'
import s6 from '../../../spine/customers/06-history/session.txt?raw'
import pit7 from '../../../spine/customers/07-point-in-time/project/globalbank/pit.py?raw'
import s7 from '../../../spine/customers/07-point-in-time/session.txt?raw'

// Course 5 — Customers and accounts from the core system (bronze → silver). Every IDE frame is a
// workspace run (spine/customers/); 5.8 (managed connectors) is documented. Numbers are read from
// the sessions.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const num = (s: string) => Number(s.replace(/,/g, ''))
const fmt = (n: number) => n.toLocaleString('en')
const FILL = { spread: true, minH: 520 } as const
const PKG = ['globalbank/__init__.py', 'globalbank/session.py', 'globalbank/land.py']
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...PKG, ...files, 'globalbank_sim/', 'land.sh'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const applied = (out: string) => {
  const m = out.match(/: ([\d,]+) changes\n\s+inserted (\d+), updated (\d+), deleted (\d+); silver\.\w+: ([\d,]+) rows/)!
  return { changes: num(m[1]), inserted: num(m[2]), updated: num(m[3]), deleted: num(m[4]), rows: num(m[5]) }
}
const apply = (table: string, files: string) => `python -m globalbank.cdc ${table} '${files}'`
const arrivals = (out: string) => all(out, /^\s+(\S+)\s+seq\s+(\d+)\s+(\w)\s+(.+)$/gm).map((m) => ({ file: m[1], seq: Number(m[2]), op: m[3], address: m[4] }))
const silverNow = (out: string) => { const m = out.match(/silver now: seq (\d+), (.+)$/m)!; return { seq: Number(m[1]), address: m[2] } }

// §1 — what the core system sends: change records, landed in bronze as received.
const landed1 = outputOf(s1, 'python -m globalbank.land core_cdc')
const total1 = num(landed1.match(/= ([\d,]+) rows/)![1])
const out1 = outputOf(s1, 'python -m globalbank.record 12155')
const counts1 = all(out1.split('\n')[0], /(\w+) (\w) ([\d,]+)/g).map((m) => ({ table: m[1], op: m[2], n: num(m[3]) }))
const head1 = out1.match(/op (\w)\s+seq (\d+)\s+table (\w+)\s+ts (.+)$/m)!
const opName: Record<string, string> = { I: 'insert', U: 'update', D: 'delete' }
const records1: SceneModel = ideFrame({
  tree: tree(['globalbank/catalog.py', 'globalbank/record.py'], 'globalbank/record.py', ['globalbank/record.py']),
  editor: { file: 'globalbank/record.py', code: record1, highlight: linesFrom(record1, 'counts = spark.sql', 'GROUP BY ALL') },
  session: s1,
  side: [
    {
      type: 'table', id: 'record', title: `One change, taken apart: seq ${head1[2]}`, tone: 'source', columns: ['field', 'value', 'means'], rows: [
        { id: 'f-op', cells: ['op', head1[1], `an ${opName[head1[1]]}`], tone: 'source' },
        { id: 'f-seq', cells: ['seq', head1[2], 'the core system’s commit order'], tone: 'source' },
        { id: 'f-ts', cells: ['ts', head1[4].split(' ')[0], 'when it changed'] },
        { id: 'f-table', cells: ['table', head1[3], 'which core table'] },
        { id: 'f-key', cells: ['key', '{"customer_id": …}', 'which row'] },
        { id: 'f-after', cells: ['after', 'the whole row, after', 'kept as JSON text in bronze'] },
      ],
    },
    {
      type: 'table', id: 'counts', title: `${fmt(total1)} changes in bronze.core_cdc`, tone: 'ingest', columns: ['table', 'op', 'records'],
      rows: counts1.map((c) => ({ id: `c-${c.table}-${c.op}`, cells: [c.table, `${c.op} (${opName[c.op]})`, fmt(c.n)], tone: c.op === 'D' ? 'consume' as const : undefined })),
    },
    {
      type: 'group', id: 'trip', title: 'One change, from commit to bronze', icon: 'workflow', tone: 'source', dir: 'row', children: [
        { type: 'item', id: 't-core', title: 'core system', sub: 'commits seq', icon: 'database' },
        { type: 'item', id: 't-cdc', title: 'CDC tool', sub: 'two files a day', icon: 'file' },
        { type: 'item', id: 't-bronze', title: 'bronze', sub: 'as received', icon: 'layers' },
      ],
    },
  ],
  edges: [
    { from: 't-core', to: 't-cdc' },
    { from: 't-cdc', to: 't-bronze', label: 'Auto Loader' },
  ],
})

// §2 — current state with MERGE: the latest change per key, applied to silver (SCD type 1).
const sept2 = applied(outputOf(s2, apply('customers', '2026-09-')))
const oct2 = applied(outputOf(s2, apply('customers', '2026-10-0[1-8]')))
const current2: SceneModel = ideFrame({
  tree: tree(['globalbank/cdc.py', 'globalbank/record.py'], 'globalbank/cdc.py', ['globalbank/cdc.py']),
  editor: { file: 'globalbank/cdc.py', code: cdc2, ...view(cdc2, 'def apply', 'return batch.count()', 0), highlight: linesFrom(cdc2, 'MERGE INTO', "WHEN NOT MATCHED AND s.op != 'D'") },
  session: s2,
  side: [
    {
      type: 'group', id: 'flow', title: 'One batch of change files', icon: 'workflow', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'b-files', title: 'the batch: files matching a pattern', sub: 'September; then 1–8 October', icon: 'folder' },
        { type: 'item', id: 'b-latest', title: 'the latest change per key', sub: 'row_number() by seq, newest first', icon: 'filter' },
        { type: 'item', id: 'b-merge', title: 'MERGE into silver.customers', sub: 'insert new, update known, delete D', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'batches', title: 'Two batches', tone: 'ingest', columns: ['batch', 'changes', 'inserted', 'updated', 'rows after'], rows: [
        { id: 'r-sept', cells: ['September', fmt(sept2.changes), fmt(sept2.inserted), fmt(sept2.updated), fmt(sept2.rows)], tone: 'ingest' },
        { id: 'r-oct', cells: ['1–8 October', fmt(oct2.changes), fmt(oct2.inserted), fmt(oct2.updated), fmt(oct2.rows)], tone: 'ingest' },
      ],
    },
  ],
  edges: [
    { from: 'b-files', to: 'b-latest' },
    { from: 'b-latest', to: 'b-merge' },
  ],
})

// §3 / §4 — out of order: the same two files, applied without and then with the sequence guard.
const OOO = ['2026-10-09/changes-1200', '2026-10-09/changes-2359']
const ooo = (session: string) => ({
  first: applied(outputOf(session, apply('customers', OOO[0]))),
  second: applied(outputOf(session, apply('customers', OOO[1]))),
  arrivals: arrivals(outputOf(session, 'python -m globalbank.customer C000001')),
  now: silverNow(outputOf(session, 'python -m globalbank.customer C000001')),
})
const o3 = ooo(s3)
const o4 = ooo(s4)
const pair = o3.arrivals.filter((a) => a.file.startsWith('2026-10-09'))
const newest = pair.reduce((a, b) => (b.seq > a.seq ? b : a))
const orderTable = (id: string, title: string, o: typeof o3) => ({
  type: 'table' as const, id, title, tone: 'source' as const, columns: ['arrived in', 'seq', 'address'],
  rows: o.arrivals.map((a) => ({ id: `${id}-${a.seq}`, cells: [a.file, String(a.seq), a.address], tone: a.seq === o.now.seq ? 'consume' as const : undefined })),
})
const outOfOrder3: SceneModel = ideFrame({
  tree: tree(['globalbank/cdc.py', 'globalbank/customer.py'], 'globalbank/customer.py', ['globalbank/customer.py']),
  editor: { file: 'globalbank/customer.py', code: customer3, highlight: linesFrom(customer3, 'SELECT regexp_extract', 'ORDER BY source_file, seq') },
  session: s3,
  side: [
    orderTable('arrivals', 'C000001’s changes, as they arrived', o3),
    {
      type: 'table', id: 'two', title: 'Two orderings, two answers', tone: 'consume', columns: ['applied by', 'last write', 'address'], rows: [
        { id: 'o-arrival', cells: ['arrival (this MERGE)', `seq ${o3.now.seq}`, o3.now.address], tone: 'consume' },
        { id: 'o-seq', cells: ['sequence (the core)', `seq ${newest.seq}`, newest.address], tone: 'ingest' },
      ],
    },
    { type: 'note', id: 'note', tone: 'consume', text: `The later change (seq ${newest.seq}) arrived first. Applying files in arrival order let the older one overwrite it: silver now holds an address the customer has already left.` },
  ],
})
const inSequence4: SceneModel = ideFrame({
  tree: tree(['globalbank/cdc.py', 'globalbank/customer.py'], 'globalbank/cdc.py'),
  editor: { file: 'globalbank/cdc.py', code: cdc4, ...view(cdc4, 'def apply', 'return batch.count()', 0), highlight: [lineOf(cdc4, "s.seq > t.seq AND s.op = 'D'"), lineOf(cdc4, 'WHEN MATCHED AND s.seq > t.seq THEN')] },
  session: s4,
  side: [
    {
      type: 'group', id: 'guard', title: 'The second file, with the guard', icon: 'shield', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'g-row', title: `silver: seq ${newest.seq}, ${newest.address}`, sub: 'written by the first file', icon: 'layers' },
        { type: 'item', id: 'g-old', title: `the change seq ${pair.find((a) => a !== newest)!.seq}`, sub: 'older than the row it would replace', icon: 'clock' },
        { type: 'item', id: 'g-skip', title: 'WHEN MATCHED AND s.seq > t.seq', sub: 'false: the row is left alone', icon: 'check' },
      ],
    },
    {
      type: 'table', id: 'files', title: 'The same two files, applied again', tone: 'ingest', columns: ['file', 'changes', 'updated'], rows: [
        { id: 'f-1', cells: [OOO[0], fmt(o4.first.changes), fmt(o4.first.updated)] },
        { id: 'f-2', cells: [OOO[1], fmt(o4.second.changes), fmt(o4.second.updated)], tone: 'ingest' },
        { id: 'f-now', cells: ['silver now', `seq ${o4.now.seq}`, o4.now.address], tone: 'ingest' },
      ],
    },
  ],
  edges: [
    { from: 'g-row', to: 'g-old', label: 'arrives later' },
    { from: 'g-old', to: 'g-skip' },
  ],
})

// §5 — deletes: an account closes; the row goes, bronze keeps the record.
const sept5 = applied(outputOf(s5, apply('accounts', '2026-09-')))
const oct5 = applied(outputOf(s5, apply('accounts', '2026-10-0')))
const closed5 = outputOf(s5, 'python -m globalbank.closed')
const dRecords = num(closed5.match(/^(\d+) D records/m)![1])
const inSilver = num(closed5.match(/; (\d+) of their accounts in silver/)![1])
const deletes5: SceneModel = ideFrame({
  tree: tree(['globalbank/cdc.py', 'globalbank/closed.py', 'globalbank/customer.py'], 'globalbank/cdc.py', ['globalbank/closed.py']),
  editor: { file: 'globalbank/cdc.py', code: cdc5, ...view(cdc5, 'TABLES = {', 'def apply', 0), highlight: linesFrom(cdc5, "'accounts': ('account_id'", "opening_balance DECIMAL(18,2)'),") },
  session: s5,
  side: [
    {
      type: 'group', id: 'gone', title: 'An account closes', icon: 'key', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'd-bronze', title: 'bronze.core_cdc: op D, key only', sub: 'appended, and kept: the closing is history', icon: 'shield' },
        { type: 'item', id: 'd-rec', title: 'the batch’s latest change: D', sub: 'WHEN MATCHED AND … s.op = \'D\' THEN DELETE', icon: 'filter' },
        { type: 'item', id: 'd-silver', title: 'silver.accounts', sub: 'the row goes: silver is what is true now', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'batches', title: 'silver.accounts, two batches', tone: 'consume', columns: ['batch', 'changes', 'inserted', 'deleted', 'rows'], rows: [
        { id: 'a-sept', cells: ['September', fmt(sept5.changes), fmt(sept5.inserted), fmt(sept5.deleted), fmt(sept5.rows)] },
        { id: 'a-oct', cells: ['1–9 October', fmt(oct5.changes), fmt(oct5.inserted), fmt(oct5.deleted), fmt(oct5.rows)], tone: 'consume' },
        { id: 'a-d', cells: ['D records in bronze', fmt(dRecords), '', '', `${inSilver} in silver`], tone: 'ingest' },
      ],
    },
    { type: 'note', id: 'note', tone: 'consume', text: `Some accounts opened and closed inside September: their latest change is the D, so they never reach silver. All ${dRecords} closings stay in bronze, with their file and sequence: when an account closed is answered there.` },
  ],
  edges: [
    { from: 'd-bronze', to: 'd-rec', label: 'MERGE' },
    { from: 'd-rec', to: 'd-silver', label: 'delete' },
  ],
})

// §6 — history: SCD type 2, one row per version with when it held.
const out6 = outputOf(s6, 'python -m globalbank.scd2 C000001')
const [, versions6, customers6] = out6.match(/: ([\d,]+) versions of ([\d,]+) customers/)!
const timeline6 = all(out6, /^\|(\d+)\s*\|(\S+ \S+)\|(\S+(?: \S+)?)\s*\|(.+?)\s*\|(\w+)\s*\|$/gm)
  .map((m) => ({ seq: m[1], from: m[2], to: m[3].trim(), address: m[4], kyc: m[5] }))
const history6: SceneModel = ideFrame({
  tree: tree(['globalbank/cdc.py', 'globalbank/customer.py', 'globalbank/scd2.py'], 'globalbank/scd2.py', ['globalbank/scd2.py']),
  editor: { file: 'globalbank/scd2.py', code: scd6, ...view(scd6, 'def build', "WHERE `table` = 'customers'", 0), highlight: linesFrom(scd6, 'lead(ts) OVER', 'valid_to IS NULL AS is_current') },
  session: s6,
  side: [
    {
      type: 'table', id: 'timeline', title: 'C000001, every version', tone: 'ingest', columns: ['valid from', 'valid to', 'address', 'KYC'],
      rows: timeline6.map((t) => ({ id: `t-${t.seq}`, cells: [t.from.slice(0, 16), t.to === 'NULL' ? 'now' : t.to.slice(0, 16), t.address, t.kyc], tone: t.to === 'NULL' ? 'ingest' as const : undefined })),
    },
    {
      type: 'table', id: 'kinds', title: 'Two silver tables, two questions', tone: 'store', columns: ['table', 'rows', 'answers'], rows: [
        { id: 'k-1', cells: ['silver.customers', fmt(num(customers6)), 'who is the customer now?'] },
        { id: 'k-2', cells: ['silver.customers_history', fmt(num(versions6)), 'who were they on a date?'], tone: 'ingest' },
      ],
    },
    { type: 'note', id: 'note', tone: 'ingest', text: 'Ordered by seq, not by arrival: the history is right even for the pair that arrived the wrong way round.' },
  ],
})

// §7 — a point-in-time join: the KYC status then, not now.
const out7 = outputOf(s7, 'python -m globalbank.pit')
const [, paid7, differ7] = out7.match(/^([\d,]+) payments; ([\d,]+) with another KYC status then/m)!
const rows7 = all(out7, /^\|(au-\S+)\s*\|(\S+ \S+)\|(C\d+)\s*\|(\w+)\s*\|(\w+)\s*\|$/gm).map((m) => m.slice(1, 6))
const pit7Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/cdc.py', 'globalbank/pit.py', 'globalbank/scd2.py'], 'globalbank/pit.py', ['globalbank/pit.py']),
  editor: { file: 'globalbank/pit.py', code: pit7, highlight: linesFrom(pit7, 'JOIN globalbank_dev.silver.customers_history h', 'OR h.valid_to IS NULL') },
  session: s7,
  side: [
    {
      type: 'table', id: 'joins', title: 'One payment, two joins', tone: 'ingest', columns: ['joined to', 'on', 'answers'], rows: [
        { id: 'j-now', cells: ['silver.customers', 'customer_id', 'the status today'] },
        { id: 'j-then', cells: ['customers_history', 'valid_from ≤ auth_ts < valid_to', 'the status then'], tone: 'ingest' },
      ],
    },
    {
      type: 'table', id: 'rows', title: `${differ7} of ${paid7} payments differ`, tone: 'consume', columns: ['auth_ts', 'customer', 'then', 'now'],
      rows: rows7.map((r) => ({ id: `p-${r[0]}`, cells: [r[1].slice(0, 16), r[2], r[3], r[4]], tone: 'consume' as const })),
    },
    { type: 'note', id: 'note', tone: 'consume', text: 'Joined to the current table, these payments look as if unverified customers made them. They did not: the status changed after they paid. Questions about the past join to history.' },
  ],
})

// §8 — ◆ managed connectors: DOCUMENTED. Lakeflow Connect reads the core database itself; Free
// Edition has no database of the bank's to connect to, so this frame shows the documented shape
// beside what this course built.
const connectors8: SceneModel = {
  title: 'Managed connectors',
  sub: 'documented (docs.databricks.com, checked 2026-10-27): not run on Free Edition',
  nodes: [
    {
      type: 'group', id: 'ours', title: 'What this course built', sub: 'run on the workspace', icon: 'terminal', tone: 'ingest', dir: 'row', children: [
        { type: 'item', id: 'o-core', title: 'core banking database', sub: 'the system of record', icon: 'database' },
        { type: 'item', id: 'o-cdc', title: 'a CDC tool', sub: 'writes change files', icon: 'workflow' },
        { type: 'item', id: 'o-vol', title: 'landing volume', sub: `${fmt(total1)} records, JSON`, icon: 'folder' },
        { type: 'item', id: 'o-code', title: 'Auto Loader + MERGE', sub: 'our code: seq guard, deletes, history', icon: 'code' },
        { type: 'item', id: 'o-silver', title: 'silver.customers', sub: 'current + history', icon: 'layers' },
      ],
    },
    {
      type: 'group', id: 'managed', title: 'Lakeflow Connect', sub: 'documented', icon: 'databricks', tone: 'infra', dir: 'row', children: [
        { type: 'item', id: 'm-core', title: 'core banking database', sub: 'SQL Server, PostgreSQL, MySQL: by CDC', icon: 'database' },
        { type: 'item', id: 'm-gw', title: 'ingestion gateway', sub: 'a continuous task: change capture, staged', icon: 'server' },
        { type: 'item', id: 'm-pipe', title: 'ingestion pipeline', sub: 'managed: ordering, deletes, schema', icon: 'workflow' },
        { type: 'item', id: 'm-st', title: 'a streaming table', sub: 'history tracking: SCD type 1 or 2', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'when', title: 'Which to use', columns: ['', 'files + your code', 'a managed connector'], rows: [
        { id: 'w-who', cells: ['who reads the source', 'a vendor’s CDC tool', 'Databricks'] },
        { id: 'w-order', cells: ['ordering and deletes', 'your MERGE (5.4, 5.5)', 'the connector'] },
        { id: 'w-fe', cells: ['on Free Edition', 'yes: this course', 'no core database to reach'], tone: 'consume' },
      ],
    },
  ],
  edges: [
    { from: 'o-core', to: 'o-cdc' }, { from: 'o-cdc', to: 'o-vol' }, { from: 'o-vol', to: 'o-code' }, { from: 'o-code', to: 'o-silver' },
    { from: 'm-core', to: 'm-gw' }, { from: 'm-gw', to: 'm-pipe' }, { from: 'm-pipe', to: 'm-st' },
  ],
}

export const customersScenes: Record<string, SceneModel> = {
  'customers-records': records1,
  'customers-current': current2,
  'customers-out-of-order': outOfOrder3,
  'customers-in-sequence': inSequence4,
  'customers-deletes': deletes5,
  'customers-history': history6,
  'customers-point-in-time': pit7Scene,
  'customers-connectors': connectors8,
}
