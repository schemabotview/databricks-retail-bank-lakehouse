import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import nightly1 from '../../../spine/schedule/01-nightly/project/resources/nightly.yml?raw'
import s1 from '../../../spine/schedule/01-nightly/session.txt?raw'
import job2 from '../../../spine/schedule/02-run/project/globalbank/job.py?raw'
import s2 from '../../../spine/schedule/02-run/session.txt?raw'
import nightly3 from '../../../spine/schedule/03-file-arrival/project/resources/nightly.yml?raw'
import s3 from '../../../spine/schedule/03-file-arrival/session.txt?raw'
import check4 from '../../../spine/schedule/04-repair/project/jobs/check.py?raw'
import s4 from '../../../spine/schedule/04-repair/session.txt?raw'
import monthEnd5 from '../../../spine/schedule/05-idempotency/project/sql/gold/month_end.sql?raw'
import s5 from '../../../spine/schedule/05-idempotency/session.txt?raw'
import monthEnd6 from '../../../spine/schedule/06-parameters/project/sql/gold/month_end.sql?raw'
import nightly6 from '../../../spine/schedule/06-parameters/project/resources/nightly.yml?raw'
import s6 from '../../../spine/schedule/06-parameters/session.txt?raw'
import nightly7 from '../../../spine/schedule/07-run-as/project/resources/nightly.yml?raw'
import s7 from '../../../spine/schedule/07-run-as/session.txt?raw'

// Course 10 — Run it every night: a Lakeflow Job, run on the owner's Free Edition workspace
// (spine/schedule/). Task states come from the Jobs API's own run records.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const FILL = { spread: true, minH: 520 } as const
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...files.filter((f) => !f.startsWith('globalbank/')), ...files.filter((f) => f.startsWith('globalbank/')), 'pipelines/'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const J = 'python -m globalbank.job'
type Task = { key: string; state: string; note: string }
const report = (out: string) => ({
  head: out.match(/^run (\w+) \((\w+)\): (\d+) tasks$/m)!,
  tasks: all(out, /^ {2}(\w+)[ \t]+(\w+|-)(?:[ \t]+(.*))?$/gm).map((m) => ({ key: m[1], state: m[2], note: m[3] ?? '' } as Task)),
})
const graph = (out: string) => all(out, /^ {2}(\w+)\s+(first|after (.+))$/gm).map((m) => ({ key: m[1], after: m[3] ? m[3].split(', ') : [] }))
const tone = (state: string) => (state === 'SUCCESS' ? 'ingest' : state === 'FAILED' ? 'consume' : undefined) as 'ingest' | 'consume' | undefined
type Node = { key: string; after: string[] }
// The graph as levels: a task runs one level after the latest task it waits for. Tasks on one level
// run at once, so the levels draw as a chain with no crossing edges; a table gives each dependency.
const levels = (tasks: Node[]) => {
  const at: Record<string, number> = {}
  const level = (t: Node): number => (at[t.key] ??= t.after.length ? 1 + Math.max(...t.after.map((a) => level(tasks.find((x) => x.key === a)!))) : 0)
  tasks.forEach(level)
  return [...new Set(Object.values(at))].sort().map((n) => tasks.filter((t) => at[t.key] === n).map((t) => t.key))
}
const chain = (tasks: Node[], states: Record<string, string> = {}) => {
  const lv = levels(tasks)
  return {
    nodes: lv.map((keys, i) => ({
      type: 'item' as const, id: `l-${i}`, title: keys.join(' · '),
      sub: keys.length > 1 ? `${keys.length} tasks at once` : i === 0 ? 'first' : 'after the level above',
      icon: keys.includes('pipeline') ? 'workflow' : keys.includes('check') ? 'check' : 'database',
      tone: keys.some((k) => states[k] === 'FAILED') ? 'consume' as const : keys.every((k) => states[k] === 'SUCCESS') ? 'ingest' as const : undefined,
    })),
    edges: lv.slice(1).map((_, i) => ({ from: `l-${i}`, to: `l-${i + 1}` })),
  }
}

// §1 — the nightly run, as a job: the task graph.
const g1 = graph(outputOf(s1, `${J} deploy`))
const c1 = chain(g1)
const nightly1Scene: SceneModel = ideFrame({
  tree: tree(['resources/nightly.yml', 'jobs/check.py', 'sql/fraud/flags.sql', 'globalbank/job.py'], 'resources/nightly.yml', ['resources/nightly.yml', 'jobs/check.py', 'sql/fraud/flags.sql', 'globalbank/job.py']),
  editor: { file: 'resources/nightly.yml', code: nightly1, lang: 'text', ...view(nightly1, '      tasks:', undefined, 0), highlight: linesFrom(nightly1, '- task_key: pipeline', 'pipeline_id: ${resources.pipelines.globalbank_pipeline.id}') },
  session: s1,
  side: [
    { type: 'group', id: 'graph', title: 'globalbank_nightly, level by level', icon: 'workflow', tone: 'ingest', ...FILL, children: c1.nodes },
    {
      type: 'table', id: 'deps', title: 'Each task, and what it waits for', tone: 'ingest', columns: ['task', 'waits for'],
      rows: g1.map((t) => ({ id: `d-${t.key}`, cells: [t.key, t.after.join(', ') || '—'] })),
    },
  ],
  edges: c1.edges,
})

// §2 — a job run: each task's state, from the run.
const r2 = report(outputOf(s2, `${J} run`))
const states2 = Object.fromEntries(r2.tasks.map((t) => [t.key, t.state]))
const c2 = chain(g1, states2)
const run2: SceneModel = ideFrame({
  tree: tree(['resources/nightly.yml', 'globalbank/job.py'], 'globalbank/job.py'),
  editor: { file: 'globalbank/job.py', code: job2, ...view(job2, "    elif verb == 'run':", undefined, 0), highlight: linesFrom(job2, 'run = w.jobs.run_now(', 'report(w, run)') },
  session: s2,
  side: [
    { type: 'group', id: 'graph', title: `run ${r2.head[1]} (${r2.head[2].replace('_', ' ')}): ${r2.head[3]} tasks`, icon: 'workflow', tone: 'ingest', ...FILL, children: c2.nodes },
    {
      type: 'table', id: 'states', title: 'Each task’s result, from the run', tone: 'ingest', columns: ['task', 'waits for', 'result'],
      rows: g1.map((t) => ({ id: `s-${t.key}`, cells: [t.key, t.after.join(', ') || '—', states2[t.key] ?? '-'], tone: tone(states2[t.key] ?? '') })),
    },
  ],
  edges: c2.edges,
})

// §3 — file arrival: a clearing file lands, the job starts.
const r3 = report(outputOf(s3, `${J} wait`))
const fileArrival3: SceneModel = ideFrame({
  tree: tree(['resources/nightly.yml', 'globalbank/job.py', 'land.sh'], 'resources/nightly.yml'),
  editor: { file: 'resources/nightly.yml', code: nightly3, lang: 'text', ...view(nightly3, 'trigger:', undefined, 0), highlight: linesFrom(nightly3, 'trigger:', 'file_arrival:') },
  session: s3,
  side: [
    {
      type: 'group', id: 'trigger', title: 'Started by a file', icon: 'bell', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'f-land', title: 'land.sh 2026-11-01 settlements', sub: 'a clearing file in the volume', icon: 'file' },
        { type: 'item', id: 'f-watch', title: 'the file arrival trigger', sub: 'checks the folder about every minute', icon: 'search' },
        { type: 'item', id: 'f-run', title: `run ${r3.head[1]}`, sub: `trigger: ${r3.head[2].toLowerCase().replace('_', ' ')}`, icon: 'workflow' },
      ],
    },
    {
      type: 'table', id: 'tasks', title: 'The run it started', tone: 'ingest', columns: ['task', 'state'],
      rows: r3.tasks.map((t) => ({ id: `s-${t.key}`, cells: [t.key, t.state], tone: tone(t.state) })),
    },
  ],
  edges: [
    { from: 'f-land', to: 'f-watch' },
    { from: 'f-watch', to: 'f-run', label: 'new file' },
  ],
})

// §4 — failure and repair.
const blocks4 = s4.split(/^\$ /m).slice(1)
const failed4 = report(blocks4.find((b) => b.startsWith(`${J} run`))!)
const repaired4 = report(blocks4.find((b) => b.startsWith(`${J} repair`))!)
// The session runs past the terminal's 13 rows (two run reports and a landing), so this section is
// a full concept scene with the real output inside it (CLAUDE.md, "Frames").
const block4 = (verb: string) => '$ ' + blocks4.find((b) => b.startsWith(`${J} ${verb}`))!.trimEnd()
const land4 = '$ ' + blocks4.find((b) => b.startsWith('bash land.sh'))!.trimEnd()
const repair4: SceneModel = {
  title: 'Failure and repair',
  sub: 'run on the workspace: one run of globalbank_nightly, failed, then repaired',
  nodes: [
    {
      type: 'group', id: 'night', title: 'The night of 31 October', icon: 'workflow', tone: 'consume', dir: 'row', children: [
        { type: 'code', id: 'check', filename: 'jobs/check.py', code: check4.split('\n').slice(lineOf(check4, 'day = sys.argv[1]') - 1, lineOf(check4, "raise SystemExit(f'no clearing file for {day}")).join('\n') },
        { type: 'code', id: 'first', terminal: true, filename: 'terminal — the run fails', code: block4('run') },
      ],
    },
    {
      type: 'group', id: 'fix', title: 'The file lands; the same run is repaired', icon: 'check', tone: 'ingest', dir: 'row', children: [
        { type: 'code', id: 'repair', terminal: true, filename: 'terminal — the run is repaired', code: `${land4}\n${block4('repair')}` },
        {
          type: 'table', id: 'states', title: 'One run, before and after repair', tone: 'ingest', columns: ['task', 'first try', 'after repair'],
          rows: failed4.tasks.map((t) => {
            const after = repaired4.tasks.find((r) => r.key === t.key)?.state ?? t.state
            return { id: `r-${t.key}`, cells: [t.key, t.state, after], tone: t.state !== after ? 'ingest' as const : tone(t.state) }
          }),
        },
      ],
    },
  ],
  edges: [{ from: 'night', to: 'fix', label: 'repair: from the pipeline down' }],
}

// §5 — idempotency: the month-end task appends on every run.
const rows5 = outputOf(s5, 'python -m globalbank.warehouse sql/gold/month_end_rows.sql').split('\n').slice(1).filter(Boolean)
const idem5: SceneModel = ideFrame({
  tree: tree(['sql/gold/month_end.sql', 'sql/gold/month_end_rows.sql', 'resources/nightly.yml'], 'sql/gold/month_end.sql', ['sql/gold/month_end.sql', 'sql/gold/month_end_rows.sql']),
  editor: { file: 'sql/gold/month_end.sql', code: monthEnd5, lang: 'sql', highlight: linesFrom(monthEnd5, 'INSERT INTO globalbank_dev.gold.month_end', 'FROM globalbank_dev.gold.monthly_statements GROUP BY month') },
  session: s5,
  side: [
    {
      type: 'table', id: 'rows', title: `gold.month_end after two runs: ${rows5.length} rows`, tone: 'consume', columns: ['month', 'accounts', 'deposits EUR'],
      rows: rows5.map((r, i) => ({ id: `m-${i}`, cells: r.trim().split(/\s{2,}/), tone: 'consume' as const })),
    },
    {
      type: 'group', id: 'why', title: 'Why a re-run doubled October', icon: 'bell', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'w-run', title: 'a job runs again', sub: 'a retry, a repair, a second trigger', icon: 'workflow' },
        { type: 'item', id: 'w-insert', title: 'INSERT INTO appends', sub: 'October, once more', icon: 'database' },
        { type: 'item', id: 'w-double', title: 'deposits counted twice', sub: 'the ledger no longer adds up', icon: 'bell' },
      ],
    },
  ],
  edges: [
    { from: 'w-run', to: 'w-insert' },
    { from: 'w-insert', to: 'w-double' },
  ],
})

// §6 — parameters and task values: the month flows from check to month_end; idempotent now.
const out6 = outputOf(s6, `${J} output check`)
const rows6 = outputOf(s6, 'python -m globalbank.warehouse sql/gold/month_end_rows.sql').split('\n').slice(1).filter(Boolean)
const params6: SceneModel = ideFrame({
  tree: tree(['sql/gold/month_end.sql', 'resources/nightly.yml', 'jobs/check.py'], 'sql/gold/month_end.sql'),
  editor: { file: 'sql/gold/month_end.sql', code: monthEnd6, lang: 'sql', highlight: [lineOf(monthEnd6, 'REPLACE WHERE month = :month'), lineOf(monthEnd6, 'WHERE month = :month')] },
  session: s6,
  side: [
    {
      type: 'group', id: 'flow', title: 'Values flowing between tasks', icon: 'workflow', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'v-param', title: 'run_date=2026-10-31', sub: 'a job parameter', icon: 'settings' },
        { type: 'item', id: 'v-check', title: 'check', sub: out6.split('\n')[0], icon: 'check' },
        { type: 'item', id: 'v-month', title: 'month_end', sub: `:month = {{tasks.check.values.month}}`, icon: 'database' },
      ],
    },
    {
      type: 'table', id: 'rows', title: `gold.month_end after two runs: ${rows6.length} row`, tone: 'ingest', columns: ['month', 'accounts', 'deposits EUR'],
      rows: rows6.map((r, i) => ({ id: `m-${i}`, cells: r.trim().split(/\s{2,}/), tone: 'ingest' as const })),
    },
  ],
  edges: [
    { from: 'v-param', to: 'v-check', label: 'argv' },
    { from: 'v-check', to: 'v-month', label: 'task value' },
  ],
})
void nightly6

// §7 — who the job runs as, and who hears of a failure.
const who7 = outputOf(s7, `${J} who`).split('\n')
const runAs7: SceneModel = ideFrame({
  tree: tree(['resources/nightly.yml', 'globalbank/job.py'], 'resources/nightly.yml'),
  editor: { file: 'resources/nightly.yml', code: nightly7, lang: 'text', ...view(nightly7, 'resources:', '      tasks:', 0), highlight: linesFrom(nightly7, 'run_as:', 'on_failure:') },
  session: s7,
  side: [
    {
      type: 'table', id: 'who', title: 'The job, as the workspace now holds it', tone: 'infra', columns: ['setting', 'value'],
      rows: who7.map((l, i) => ({ id: `w-${i}`, cells: l.split(': '), tone: 'infra' as const })),
    },
    {
      type: 'table', id: 'better', title: 'In production (documented)', tone: 'infra', columns: ['', 'run as', 'why'], rows: [
        { id: 'b-user', cells: ['here', 'a person', 'this course has one user: Ana'] },
        { id: 'b-sp', cells: ['a bank', 'a service principal', 'a job outlives its author’s account'] },
      ],
    },
    { type: 'note', id: 'note', tone: 'infra', text: 'Documented (docs.databricks.com, checked 2026-10-28): a service principal is made in the account console, which Free Edition does not have, so this job runs as its one user.' },
  ],
})

export const scheduleScenes: Record<string, SceneModel> = {
  'schedule-nightly': nightly1Scene,
  'schedule-run': run2,
  'schedule-file-arrival': fileArrival3,
  'schedule-repair': repair4,
  'schedule-idempotency': idem5,
  'schedule-parameters': params6,
  'schedule-run-as': runAs7,
}
