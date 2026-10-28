import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import drift1 from '../../../spine/ship/01-drift/project/globalbank/drift.py?raw'
import s1 from '../../../spine/ship/01-drift/session.txt?raw'
import bundle2 from '../../../spine/ship/02-bundle/project/databricks.yml?raw'
import s2 from '../../../spine/ship/02-bundle/session.txt?raw'
import dashboard3 from '../../../spine/ship/03-resources/project/resources/dashboard.yml?raw'
import s3 from '../../../spine/ship/03-resources/session.txt?raw'
import bundle4 from '../../../spine/ship/04-targets/project/databricks.yml?raw'
import s4 from '../../../spine/ship/04-targets/session.txt?raw'
import nightly5 from '../../../spine/ship/05-deploy-run/project/resources/nightly.yml?raw'
import s5 from '../../../spine/ship/05-deploy-run/session.txt?raw'
import test6 from '../../../spine/ship/06-tests/project/tests/test_transforms.py?raw'
import s6 from '../../../spine/ship/06-tests/session.txt?raw'
import workflow7 from '../../../spine/ship/07-ci/project/.github/workflows/deploy.yml?raw'
import s7 from '../../../spine/ship/07-ci/session.txt?raw'

// Course 11 — Ship it as code: a Declarative Automation Bundle, run on the owner's Free Edition
// workspace (spine/ship/). 11.1–11.6 are workspace runs (11.6's unit tests run local); the prod
// target is validated, not deployed (one workspace); 11.7's deploy from GitHub is documented.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const FILL = { spread: true, minH: 520 } as const
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...files, 'globalbank/', 'pipelines/', 'sql/'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const B = 'databricks bundle'
const field = (out: string, name: string) => out.match(new RegExp(`^\\s*${name}: (.*)$`, 'm'))?.[1] ?? ''

// §1 — the workspace is not git: a click changes the deployed job, and the repo never hears of it.
const out1 = outputOf(s1, 'python -m globalbank.drift')
const drift = all(out1, /^ {2}(\w+)\s+repo: (.*?)\s+workspace: (.*)$/gm).map((m) => ({ key: m[1], repo: m[2], live: m[3] }))
const drift1Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/drift.py', 'resources/nightly.yml'], 'globalbank/drift.py', ['globalbank/drift.py']),
  editor: { file: 'globalbank/drift.py', code: drift1, highlight: linesFrom(drift1, 'edited = w.jobs.get(job_id(w)).settings', 'w.jobs.reset(job_id(w), new_settings=edited)') },
  session: s1,
  side: [
    {
      type: 'group', id: 'where', title: 'Two copies of one job', icon: 'git-branch', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'w-repo', title: 'resources/nightly.yml', sub: 'in the repo: reviewed, versioned', icon: 'file' },
        { type: 'item', id: 'w-job', title: 'globalbank_nightly', sub: 'in the workspace: what actually runs', icon: 'workflow' },
        { type: 'item', id: 'w-click', title: 'someone edits it in the UI', sub: 'no commit, no review, no history', icon: 'bell', tone: 'consume' },
      ],
    },
    {
      type: 'table', id: 'diff', title: `Drift: ${drift.length} settings differ`, tone: 'consume', columns: ['setting', 'repo', 'workspace'],
      rows: drift.map((d) => ({ id: `d-${d.key}`, cells: [d.key, d.repo, d.live], tone: 'consume' as const })),
    },
  ],
  edges: [
    { from: 'w-repo', to: 'w-job', label: 'job.py deploy' },
    { from: 'w-click', to: 'w-job', label: 'edits' },
  ],
})

// §2 — a bundle: databricks.yml, and the resources it includes.
const out2 = outputOf(s2, `${B} validate`)
const bundle2Scene: SceneModel = ideFrame({
  tree: tree(['.gitignore', 'databricks.yml', 'resources/globalbank_pipeline.yml', 'resources/nightly.yml', 'dashboards/'], 'databricks.yml', ['.gitignore', 'databricks.yml', 'resources/globalbank_pipeline.yml']),
  editor: { file: 'databricks.yml', code: bundle2, lang: 'text', highlight: linesFrom(bundle2, 'bundle:', '  - resources/*.yml') },
  session: s2,
  side: [
    {
      type: 'group', id: 'parts', title: `bundle ${field(out2, 'Name')}: its parts`, icon: 'package', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'p-root', title: 'databricks.yml', sub: 'the bundle: name, variables, targets', icon: 'file' },
        { type: 'item', id: 'p-res', title: 'resources/*.yml', sub: 'the pipeline, the nightly job', icon: 'layers' },
        { type: 'item', id: 'p-code', title: 'the code it syncs', sub: 'pipelines/, sql/, jobs/, globalbank/', icon: 'code' },
        { type: 'item', id: 'p-ws', title: field(out2, 'Path').replace(/^\/Workspace/, '') || 'the bundle folder', sub: `target ${field(out2, 'Target')}: where it deploys`, icon: 'databricks' },
      ],
    },
  ],
  edges: [
    { from: 'p-root', to: 'p-res', label: 'include' },
    { from: 'p-res', to: 'p-code', label: 'points at' },
    { from: 'p-code', to: 'p-ws', label: 'sync' },
  ],
})

// §3 — resources: each YAML key becomes one workspace object, with the target's name.
const out3 = outputOf(s3, `${B} summary`)
const res3 = all(out3, /^ {2}(\w+):\n {4}(\w+):\n {6}Name: (.*)$/gm).map((m) => ({ kind: m[1], key: m[2], name: m[3] }))
const resources3: SceneModel = ideFrame({
  tree: tree(['databricks.yml', 'resources/dashboard.yml', 'resources/globalbank_pipeline.yml', 'resources/nightly.yml'], 'resources/dashboard.yml', ['resources/dashboard.yml']),
  editor: { file: 'resources/dashboard.yml', code: dashboard3, lang: 'text' },
  session: s3,
  side: [
    {
      type: 'table', id: 'res', title: `YAML key → workspace resource (${res3.length})`, tone: 'ingest', columns: ['kind', 'key in the bundle', 'name in dev'],
      rows: res3.map((r) => ({ id: `r-${r.key}`, cells: [r.kind.toLowerCase(), r.key, r.name] })),
    },
    {
      type: 'group', id: 'how', title: 'One file per resource', icon: 'package', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'h-yml', title: 'resources/dashboard.yml', sub: 'the statements dashboard of Course 8', icon: 'file' },
        { type: 'item', id: 'h-var', title: '${var.warehouse_id}', sub: 'looked up by name at deploy time', icon: 'search' },
        { type: 'item', id: 'h-ws', title: 'a Lakeview dashboard', sub: 'not deployed yet: summary only reads', icon: 'chart-bar' },
      ],
    },
  ],
  edges: [
    { from: 'h-yml', to: 'h-var' },
    { from: 'h-var', to: 'h-ws' },
  ],
})

// §4 — targets: one bundle, dev and prod.
const dev4 = outputOf(s4, `${B} validate -t dev | sed -n 1,5p`)
const prod4 = outputOf(s4, `${B} validate -t prod | sed -n 1,5p`)
const targets4: SceneModel = ideFrame({
  tree: tree(['databricks.yml', 'resources/'], 'databricks.yml'),
  editor: { file: 'databricks.yml', code: bundle4, lang: 'text', ...view(bundle4, 'variables:', undefined, 0), highlight: linesFrom(bundle4, 'targets:', 'root_path:') },
  session: s4,
  side: [
    {
      type: 'group', id: 'one', title: 'One bundle, two targets', icon: 'package', tone: 'ingest', dir: 'row', children: [
        { type: 'item', id: 't-bundle', title: 'globalbank', sub: 'one set of files', icon: 'package' },
        { type: 'item', id: 't-dev', title: 'dev', sub: 'prefixed, schedules paused', icon: 'code', tone: 'ingest' },
        { type: 'item', id: 't-prod', title: 'prod', sub: 'validated here, not deployed', icon: 'databricks', tone: 'consume' },
      ],
    },
    {
      type: 'table', id: 'diff', title: 'What each target changes', tone: 'ingest', columns: ['', 'dev', 'prod'], rows: [
        { id: 'x-path', cells: ['folder', field(dev4, 'Path').replace(/^.*\.bundle/, '….bundle'), field(prod4, 'Path').replace(/^.*\.bundle/, '….bundle')] },
        { id: 'x-mode', cells: ['mode', 'development', 'production'] },
        { id: 'x-name', cells: ['names', 'dev_ana_globalbank_…', 'globalbank_…'] },
        { id: 'x-cat', cells: ['pipeline catalog', 'globalbank_dev', 'globalbank_prod'] },
        { id: 'x-sched', cells: ['triggers', 'paused', 'live'] },
      ],
    },
    { type: 'note', id: 'note', tone: 'consume', text: 'Free Edition has one workspace and one pipeline per type, so prod is validated, not deployed. A real bank’s prod is another workspace, and the prod target names its host.' },
  ],
  edges: [
    { from: 't-bundle', to: 't-dev' },
    { from: 't-bundle', to: 't-prod' },
  ],
})

// §5 — validate, deploy, run.
const deploy5 = outputOf(s5, `${B} deploy`).split('\n').filter(Boolean).map((l) => l.replace(/ to \/Workspace\S+/, ' to the bundle folder'))
const run5 = outputOf(s5, `${B} run globalbank_nightly 2>&1 | grep TERMINATED`)
const state5 = run5.match(/"([^"]+)" (\w+)(?: (\w+))?/)
const deployRun5: SceneModel = ideFrame({
  tree: tree(['databricks.yml', 'resources/nightly.yml', 'resources/globalbank_pipeline.yml', 'resources/dashboard.yml'], 'resources/nightly.yml'),
  editor: { file: 'resources/nightly.yml', code: nightly5, lang: 'text', ...view(nightly5, '      tasks:', undefined, 0), highlight: linesFrom(nightly5, 'pipeline_id: ${resources.pipelines.globalbank_pipeline.id}') },
  session: s5,
  side: [
    {
      type: 'group', id: 'flow', title: 'databricks bundle deploy, then run', icon: 'upload', tone: 'ingest', ...FILL, children: [
        ...deploy5.map((line, i) => ({ type: 'item' as const, id: `d-${i}`, title: line.replace(/\.\.\.$/, ''), icon: i === deploy5.length - 1 ? 'check' : 'upload' })),
        { type: 'item', id: 'd-run', title: state5 ? state5[1] : 'globalbank_nightly', sub: state5 ? `${state5[2]} ${state5[3] ?? ''}`.trim() : '', icon: 'workflow', tone: 'ingest' },
      ],
    },
  ],
  edges: [...deploy5.map((_, i) => ({ from: `d-${i}`, to: i + 1 < deploy5.length ? `d-${i + 1}` : 'd-run' }))],
})

// §6 — tests: unit tests on local PySpark, one integration test on the workspace.
const unit6 = outputOf(s6, '.venv-test/bin/python -m pytest -q tests/test_transforms.py 2>&1 | tail -1')
const ws6 = outputOf(s6, 'python -m pytest -q tests/test_workspace.py 2>&1 | tail -1')
const passed = (out: string) => out.match(/(\d+) passed/)?.[1] ?? '0'
const tests6: SceneModel = ideFrame({
  tree: tree(['tests/test_transforms.py', 'tests/test_workspace.py', 'globalbank/transforms.py', 'requirements.txt'], 'tests/test_transforms.py', ['tests/test_transforms.py', 'tests/test_workspace.py', 'globalbank/transforms.py']),
  editor: { file: 'tests/test_transforms.py', code: test6, ...view(test6, '@pytest.fixture', undefined, 0), highlight: linesFrom(test6, 'def test_velocity_counts_ten_minutes', '[1, 2, 3, 4, 5, 6, 1]') },
  session: s6,
  side: [
    {
      type: 'group', id: 'pyramid', title: 'The test pyramid', icon: 'check', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'p-ws', title: `${passed(ws6)} integration test`, sub: 'Databricks Connect: real silver, the 22 Oct ring', icon: 'databricks', tone: 'consume' },
        { type: 'item', id: 'p-unit', title: `${passed(unit6)} unit tests`, sub: 'local PySpark: no workspace, seconds, run local', icon: 'code', tone: 'ingest' },
        { type: 'item', id: 'p-fn', title: 'globalbank/transforms.py', sub: 'transforms as functions of DataFrames', icon: 'file' },
      ],
    },
  ],
  edges: [
    { from: 'p-fn', to: 'p-unit', label: 'many, fast' },
    { from: 'p-unit', to: 'p-ws', label: 'few, real' },
  ],
})

// §7 — CI: the workflow is real; deploying from GitHub is documented (a service principal's OAuth
// secret needs the account console, which Free Edition does not have).
const out7 = outputOf(s7, `${B} validate -t prod | tail -1`)
const ci7: SceneModel = ideFrame({
  tree: tree(['.github/workflows/deploy.yml', 'databricks.yml', 'tests/'], '.github/workflows/deploy.yml', ['.github/workflows/deploy.yml']),
  editor: { file: '.github/workflows/deploy.yml', code: workflow7, lang: 'text', highlight: linesFrom(workflow7, '  deploy:', 'run: databricks bundle deploy -t prod') },
  session: s7,
  side: [
    {
      type: 'group', id: 'ci', title: 'Pull request → test → deploy', icon: 'git-branch', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'c-pr', title: 'a pull request', sub: 'a change to the code or the YAML', icon: 'git-branch' },
        { type: 'item', id: 'c-test', title: 'test', sub: 'pytest on local PySpark, on every PR', icon: 'check' },
        { type: 'item', id: 'c-merge', title: 'merge to main', sub: 'a reviewer approves', icon: 'git-merge' },
        { type: 'item', id: 'c-deploy', title: 'bundle deploy -t prod', sub: `as a service principal · here: ${out7}`, icon: 'databricks', tone: 'consume' },
      ],
    },
    { type: 'note', id: 'note', tone: 'consume', text: 'Documented (docs.databricks.com, checked 2026-10-27): deploying from GitHub needs a service principal’s OAuth secret, made in the account console, which Free Edition does not have. The prod validate ran on the workspace.' },
  ],
  edges: [
    { from: 'c-pr', to: 'c-test' },
    { from: 'c-test', to: 'c-merge', label: 'green' },
    { from: 'c-merge', to: 'c-deploy' },
  ],
})

export const shipScenes: Record<string, SceneModel> = {
  'ship-drift': drift1Scene,
  'ship-bundle': bundle2Scene,
  'ship-resources': resources3,
  'ship-targets': targets4,
  'ship-deploy-run': deployRun5,
  'ship-tests': tests6,
  'ship-ci': ci7,
}
