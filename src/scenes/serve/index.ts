import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import warehouse1 from '../../../spine/serve/01-warehouse/project/globalbank/warehouse.py?raw'
import s1 from '../../../spine/serve/01-warehouse/session.txt?raw'
import balances2 from '../../../spine/serve/02-daily-balances/project/sql/gold/daily_balances.sql?raw'
import s2 from '../../../spine/serve/02-daily-balances/session.txt?raw'
import statements3 from '../../../spine/serve/03-statements/project/sql/gold/monthly_statements.sql?raw'
import s3 from '../../../spine/serve/03-statements/session.txt?raw'
import asof4 from '../../../spine/serve/04-as-of/project/globalbank/asof.py?raw'
import s4 from '../../../spine/serve/04-as-of/session.txt?raw'
import dashboard5 from '../../../spine/serve/05-dashboard/project/globalbank/dashboard.py?raw'
import s5 from '../../../spine/serve/05-dashboard/session.txt?raw'
import alert6 from '../../../spine/serve/06-alerts/project/globalbank/alert.py?raw'
import s6 from '../../../spine/serve/06-alerts/session.txt?raw'
import slow7 from '../../../spine/serve/07-slow-query/project/globalbank/slow.py?raw'
import s7 from '../../../spine/serve/07-slow-query/session.txt?raw'

// Course 8 — Serve the business (silver → gold). Every frame is a workspace run (spine/serve/): gold
// is built by SQL files on the SQL warehouse, and the dashboard and alert are drawn from their own
// queries' results, never screenshotted.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const num = (s: string) => Number(s.replace(/,/g, ''))
const FILL = { spread: true, minH: 520 } as const
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...files.filter((f) => !f.startsWith('globalbank/')), 'globalbank/session.py', ...files.filter((f) => f.startsWith('globalbank/')), 'pipelines/'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const WH = 'python -m globalbank.warehouse'
/** The aligned columns warehouse.py prints: a header line, then rows. */
const grid = (out: string) => {
  const lines = out.split('\n').filter((l) => l.trim())
  const split = (l: string) => l.trim().split(/\s{2,}/)
  return { columns: split(lines[0]), rows: lines.slice(1).map(split) }
}

// §1 — a SQL warehouse, queried from the laptop.
const about1 = outputOf(s1, `${WH} --about`)
const [whName, whRest] = about1.split(': ')
const spend1 = grid(outputOf(s1, `${WH} sql/gold/card_spend.sql`))
const warehouse1Scene: SceneModel = ideFrame({
  tree: tree(['sql/gold/card_spend.sql', 'globalbank/warehouse.py'], 'globalbank/warehouse.py', ['globalbank/warehouse.py', 'sql/gold/card_spend.sql']),
  editor: { file: 'globalbank/warehouse.py', code: warehouse1, ...view(warehouse1, 'def run(w, sql'), highlight: linesFrom(warehouse1, 'r = w.statement_execution.execute_statement(', 'for k, v in params.items()])') },
  session: s1,
  side: [
    {
      type: 'group', id: 'path', title: 'One statement, end to end', icon: 'database', tone: 'serve', ...FILL, children: [
        { type: 'item', id: 'p-laptop', title: 'warehouse.py', sub: 'the SDK’s statement execution API', icon: 'code' },
        { type: 'item', id: 'p-wh', title: whName, sub: whRest, icon: 'database' },
        { type: 'item', id: 'p-gold', title: 'gold.card_spend_daily', sub: 'the pipeline keeps it current', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'rows', title: 'What it answered', tone: 'serve', columns: spend1.columns,
      rows: spend1.rows.map((r, i) => ({ id: `r-${i}`, cells: r })),
    },
  ],
  edges: [
    { from: 'p-laptop', to: 'p-wh', label: 'HTTPS' },
    { from: 'p-wh', to: 'p-gold', label: 'SQL' },
  ],
})

// §2 — daily balances: one account's October, a week to a row.
const built2 = grid(outputOf(s2, `${WH} sql/gold/daily_balances.sql`))
const weeks2 = grid(outputOf(s2, `${WH} sql/gold/balance_of.sql account=A0000011`))
const days2 = weeks2.rows.flatMap((r) => r.slice(1).map(num)) // a week to a row, a day to a column
const top2 = Math.ceil(Math.max(...days2) / 1000) * 1000
const low2 = Math.min(0, Math.floor(Math.min(...days2) / 1000) * 1000)
const balances2Scene: SceneModel = ideFrame({
  tree: tree(['sql/gold/daily_balances.sql', 'sql/gold/balance_of.sql', 'globalbank/warehouse.py'], 'sql/gold/daily_balances.sql', ['sql/gold/daily_balances.sql', 'sql/gold/balance_of.sql']),
  editor: { file: 'sql/gold/daily_balances.sql', code: balances2, lang: 'sql', ...view(balances2, 'CREATE OR REPLACE TABLE', 'LEFT JOIN daily m'), highlight: linesFrom(balances2, 'SELECT a.account_id, d.day,', 'PARTITION BY a.account_id ORDER BY d.day) AS balance') },
  session: s2,
  side: [
    {
      type: 'plot', id: 'balance', compact: true, title: 'A0000011, balance each evening of October, EUR',
      x: { labels: days2.map((_, i) => (i % 5 === 0 ? `${i + 1}` : '')) }, y: { min: low2, max: top2, step: (top2 - low2) / 4 },
      series: [{ kind: 'line', points: days2.map((b, i) => [i, b] as [number, number]), tone: 'store' }],
    },
    {
      type: 'table', id: 'made', title: 'gold.daily_balances', tone: 'store', columns: built2.columns,
      rows: built2.rows.map((r, i) => ({ id: `b-${i}`, cells: r })),
    },
    { type: 'note', id: 'note', tone: 'store', text: 'Opening balance, plus the core system’s postings, minus what cards cleared, summed day by day: one row per account per day. Salary lands on the 25th; rent leaves on the 1st.' },
  ],
})

// §3 — the monthly statement.
const st3 = grid(outputOf(s3, `${WH} sql/gold/statement_of.sql account=A0000011`))
const made3 = grid(outputOf(s3, `${WH} sql/gold/monthly_statements.sql`))
const statements3Scene: SceneModel = ideFrame({
  tree: tree(['sql/gold/daily_balances.sql', 'sql/gold/monthly_statements.sql', 'sql/gold/statement_of.sql'], 'sql/gold/monthly_statements.sql', ['sql/gold/monthly_statements.sql', 'sql/gold/statement_of.sql']),
  editor: { file: 'sql/gold/monthly_statements.sql', code: statements3, lang: 'sql', ...view(statements3, 'core AS (', "WHERE b.day = DATE'2026-10-31'"), highlight: linesFrom(statements3, "SELECT '2026-10' AS month", 'b.balance AS closing') },
  session: s3,
  side: [
    {
      type: 'table', id: 'statement', title: 'A0000011, October 2026', tone: 'store', columns: ['', 'EUR'],
      rows: st3.rows.map((r) => ({ id: `s-${r[0].replace(/\W+/g, '-')}`, cells: r, tone: /balance/.test(r[0]) ? 'store' as const : undefined })),
    },
    {
      type: 'table', id: 'made', title: 'gold.monthly_statements', tone: 'store', columns: made3.columns,
      rows: made3.rows.map((r, i) => ({ id: `m-${i}`, cells: r })),
    },
    { type: 'note', id: 'note', tone: 'store', text: 'The last line is a check, not an entry: opening − cards + salary + rent + transfers − closing must be zero, or the statement does not add up.' },
  ],
})

// §4 — the regulator's question: as reported, and as restated after late clearing files.
const out4 = outputOf(s4, 'python -m globalbank.asof')
const heads4 = out4.match(/^as reported: version (\d+)\s+as restated: version (\d+)$/m)!
const rows4 = grid(out4.split('\n').slice(1).join('\n'))
const col4 = (name: string) => rows4.columns.indexOf(name)
const asof4Scene: SceneModel = ideFrame({
  tree: tree(['sql/gold/regulatory_snapshot.sql', 'globalbank/asof.py', 'globalbank/warehouse.py'], 'globalbank/asof.py', ['sql/gold/regulatory_snapshot.sql', 'globalbank/asof.py']),
  editor: { file: 'globalbank/asof.py', code: asof4, highlight: [lineOf(asof4, 'TIMESTAMP AS OF')] },
  session: s4,
  side: [
    {
      type: 'table', id: 'two', title: 'Card book: cleared EUR, then and now', tone: 'serve', columns: ['day', 'approved', `as reported (v${heads4[1]})`, `as restated (v${heads4[2]})`],
      rows: rows4.rows.map((r) => ({ id: `d-${r[0]}`, cells: [r[0], r[col4('approved')], r[col4('eur_then')], r[col4('eur_now')]], tone: r[col4('eur_then')] !== r[col4('eur_now')] ? 'serve' as const : undefined })),
    },
    {
      type: 'group', id: 'why', title: 'Why the numbers moved', icon: 'clock', tone: 'serve', ...FILL, children: [
        { type: 'item', id: 'w-report', title: '31 October: the report is written', sub: 'what had cleared by then', icon: 'file' },
        { type: 'item', id: 'w-late', title: '1–3 November: clearing files land', sub: 'payments made in October, settled late', icon: 'building' },
        { type: 'item', id: 'w-asof', title: 'TIMESTAMP AS OF the first write', sub: 'what the bank said, still readable', icon: 'search' },
      ],
    },
  ],
  edges: [
    { from: 'w-report', to: 'w-late' },
    { from: 'w-late', to: 'w-asof', label: 'rebuilt' },
  ],
})

// §5 — gold.accounts, then a dashboard drawn from its datasets' results (each printed on one line).
const acc5 = grid(outputOf(s5, `${WH} sql/gold/accounts.sql`))
const out5 = outputOf(s5, 'python -m globalbank.dashboard')
const sets5 = all(out5, /^-- (.*) \((.*)\)\n(.*)$/gm).map((m) => ({ name: m[1], rows: m[3].split(' · ').map((r) => r.split(' ')) }))
const bars = (rows: string[][], col: number) => rows.map((r, i) => [i, num(r[col])] as [number, number])
const ceil = (rows: string[][], col: number, step: number) => Math.ceil(Math.max(...rows.map((r) => num(r[col]))) / step) * step
const [region5, segment5] = sets5
const dashboard5Scene: SceneModel = ideFrame({
  tree: tree(['sql/gold/accounts.sql', 'dashboards/statements.lvdash.json', 'globalbank/dashboard.py'], 'globalbank/dashboard.py', ['sql/gold/accounts.sql', 'dashboards/statements.lvdash.json', 'globalbank/dashboard.py']),
  editor: { file: 'globalbank/dashboard.py', code: dashboard5, ...view(dashboard5, 'w.lakeview.publish'), highlight: linesFrom(dashboard5, 'w.lakeview.publish', "print(' · '.join(") },
  session: s5,
  side: [
    {
      type: 'table', id: 'accounts', title: 'gold.accounts: what the charts group by', tone: 'store', columns: acc5.columns,
      rows: acc5.rows.map((r, i) => ({ id: `a-${i}`, cells: r })),
    },
    {
      type: 'plot', id: 'region', compact: true, title: `${region5.name}, EUR`,
      x: { labels: region5.rows.map((r) => r[0]) }, y: { min: 0, max: ceil(region5.rows, 1, 500000), step: ceil(region5.rows, 1, 500000) / 4 },
      series: [{ kind: 'bar', points: bars(region5.rows, 1), tone: 'serve' }],
    },
    {
      type: 'plot', id: 'segment', compact: true, title: `${segment5.name}: average EUR`,
      x: { labels: segment5.rows.map((r) => `${r[0]} (${r[1]})`) }, y: { min: 0, max: ceil(segment5.rows, 2, 5000), step: ceil(segment5.rows, 2, 5000) / 4 },
      series: [{ kind: 'bar', points: bars(segment5.rows, 2), tone: 'store' }],
    },
    { type: 'note', id: 'note', tone: 'serve', text: 'Both datasets read gold only: monthly_statements joined to gold.accounts. Drawn from the datasets’ own results on the warehouse; the dashboard’s page is never screenshotted.' },
  ],
})

// §6 — alerts: the overdraft query, and the alert that runs it.
const q6 = grid(outputOf(s6, `${WH} sql/alerts/overdrawn.sql`))
const made6 = outputOf(s6, 'python -m globalbank.alert').split('\n')
const alerts6Scene: SceneModel = ideFrame({
  tree: tree(['sql/alerts/overdrawn.sql', 'globalbank/alert.py', 'globalbank/warehouse.py'], 'globalbank/alert.py', ['sql/alerts/overdrawn.sql', 'globalbank/alert.py']),
  editor: { file: 'globalbank/alert.py', code: alert6, ...view(alert6, 'evaluation=sql.AlertV2Evaluation('), highlight: linesFrom(alert6, 'evaluation=sql.AlertV2Evaluation(', "timezone_id='Europe/Amsterdam'))") },
  session: s6,
  side: [
    {
      type: 'table', id: 'rows', title: 'What the query sees now', tone: 'consume', columns: q6.columns,
      rows: q6.rows.map((r, i) => ({ id: `o-${i}`, cells: r, tone: 'consume' as const })),
    },
    {
      type: 'group', id: 'rule', title: made6[0], icon: 'bell', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'a-query', title: 'the query, on the warehouse', sub: 'every day at 07:00', icon: 'database' },
        { type: 'item', id: 'a-cond', title: 'SUM(accounts) > 0', sub: 'the condition', icon: 'filter' },
        { type: 'item', id: 'a-notify', title: 'notify the owner', sub: 'by email: documented, not sent here', icon: 'bell' },
      ],
    },
  ],
  edges: [
    { from: 'a-query', to: 'a-cond' },
    { from: 'a-cond', to: 'a-notify', label: 'true' },
  ],
})

// §7 — why a query is slow: what each statement read, from the query history.
const q7 = grid(outputOf(s7, 'python -m globalbank.slow'))
const slow7Scene: SceneModel = ideFrame({
  tree: tree(['sql/gold/point.sql', 'globalbank/slow.py', 'globalbank/warehouse.py'], 'globalbank/slow.py', ['sql/gold/point.sql', 'globalbank/slow.py']),
  editor: { file: 'globalbank/slow.py', code: slow7, ...view(slow7, 'RECENT = ', undefined, 0), highlight: linesFrom(slow7, 'read_files AS files', 'FROM system.query.history') },
  session: s7,
  side: [
    {
      type: 'table', id: 'history', title: 'system.query.history: this session’s statements', tone: 'serve', columns: q7.columns,
      rows: q7.rows.map((r, i) => ({ id: `h-${i}`, cells: r })),
    },
    {
      type: 'group', id: 'read', title: 'What makes a query slow', icon: 'activity', tone: 'serve', ...FILL, children: [
        { type: 'item', id: 'k-files', title: 'files read', sub: 'every file opened costs a request', icon: 'file' },
        { type: 'item', id: 'k-pruned', title: 'files pruned', sub: 'skipped by their min / max statistics', icon: 'filter' },
        { type: 'item', id: 'k-fix', title: 'fewer, better-laid-out files', sub: 'Course 12: OPTIMIZE, liquid clustering', icon: 'layers' },
      ],
    },
  ],
  edges: [
    { from: 'k-files', to: 'k-pruned' },
    { from: 'k-pruned', to: 'k-fix' },
  ],
})

export const serveScenes: Record<string, SceneModel> = {
  'serve-warehouse': warehouse1Scene,
  'serve-balances': balances2Scene,
  'serve-statements': statements3Scene,
  'serve-as-of': asof4Scene,
  'serve-dashboard': dashboard5Scene,
  'serve-alerts': alerts6Scene,
  'serve-slow-query': slow7Scene,
}
