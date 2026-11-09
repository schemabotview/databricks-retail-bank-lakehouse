import type { SceneModel } from '@graphlearning/graphl-flow'
import { lineOf, linesFrom } from '../ide'
import { ideFrame2 } from '../frame'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import readme from '../../../spine/start/01-cli/project/README.md?raw'
import s1 from '../../../spine/start/01-cli/session.txt?raw'
import s2 from '../../../spine/start/02-where-code-runs/session.txt?raw'
import sessionPy from '../../../spine/start/03-connect/project/globalbank/session.py?raw'
import s3 from '../../../spine/start/03-connect/session.txt?raw'
import catalogPy from '../../../spine/start/04-catalog/project/globalbank/catalog.py?raw'
import s4 from '../../../spine/start/04-catalog/session.txt?raw'
import landSh from '../../../spine/start/05-land/project/land.sh?raw'
import s5 from '../../../spine/start/05-land/session.txt?raw'
import firstTable from '../../../spine/start/06-first-table/project/globalbank/first_table.py?raw'
import s6 from '../../../spine/start/06-first-table/session.txt?raw'

// Course 2 — A workspace and a first table. Every frame is RUN on the owner's Free Edition workspace
// (serverless) and replayed by scripts/spine.py; the host, user and ids are normalised there. Every
// number below is read from a session, never typed.

const PKG = ['globalbank/__init__.py', 'globalbank/session.py']
// The venv from 2.3; landing/ (the generator's local files) only from 2.5, when it first exists.
const VENV = ['.venv/']
const LANDED = ['.venv/', 'landing/']
// Frame v2: the side pane spreads its blocks over its height itself (frame.ts); a block needs no floor.
const FILL = {} as const

// §1 — the CLI, and how it finds the workspace.
const cliVersion = outputOf(s1, 'databricks --version').replace('Databricks CLI ', '')
const authAs = outputOf(s1, 'databricks auth describe | head -3').match(/Authenticated with: (\w+)/)![1]
const warehouse = outputOf(s1, 'databricks warehouses list').split('\n')[1].trim().split(/\s{2,}/)
const startCli: SceneModel = ideFrame2({
  model: 'A command, an API call, the workspace',
  tree: explorer({ files: ['README.md'], mark: { 'README.md': 'active' } }),
  editor: { file: 'README.md', code: readme, lang: 'text', highlight: linesFrom(readme, 'export DATABRICKS_HOST', 'export DATABRICKS_TOKEN') },
  session: s1,
  side: [
    {
      type: 'group', id: 'path', title: 'One command, end to end', icon: 'terminal', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'p-env', title: 'DATABRICKS_HOST, _TOKEN', sub: 'the environment: who and where', icon: 'key' },
        { type: 'item', id: 'p-cli', title: `Databricks CLI ${cliVersion}`, sub: 'one Go binary on the laptop', icon: 'terminal' },
        { type: 'item', id: 'p-api', title: 'the workspace REST API', sub: 'HTTPS, one call per command', icon: 'globe' },
        { type: 'item', id: 'p-ws', title: 'the workspace', sub: `found one ${warehouse[2]} SQL warehouse`, icon: 'databricks' },
      ],
    },
    {
      type: 'table', id: 'ways', title: 'Three ways to sign in', tone: 'ingest', columns: ['way', 'used for'], rows: [
        { id: 'w-env', cells: [`env (${authAs})`, 'replays, CI'], tone: 'ingest' },
        { id: 'w-profile', cells: ['~/.databrickscfg', 'a profile each'] },
        { id: 'w-oauth', cells: ['auth login', 'OAuth: people'] },
      ],
    },
  ],
  edges: [
    { from: 'p-env', to: 'p-cli' },
    { from: 'p-cli', to: 'p-api' },
    { from: 'p-api', to: 'p-ws' },
  ],
})

// §2 — ◆ full scene: where your code runs. The lab's real answers; the planes are documented.
const described = outputOf(s2, 'databricks auth describe').split('\n')
const pick = (key: string) => described.find((l) => l.includes(`${key}:`))!.trim().replace(/^✓ /, '')
const excerpt = ['Host:', 'User:', 'Authenticated with:'].map((k) => described.find((l) => l.startsWith(k))!)
  .concat(pick('workspace_id').split(' (')[0], pick('cloud'))
const startWhere: SceneModel = {
  title: 'Where your code runs',
  sub: 'a workspace is three planes; on Free Edition all compute is serverless',
  nodes: [
    {
      type: 'group', id: 'planes', bare: true, dir: 'row', children: [
        {
          type: 'group', id: 'laptop', badge: 1, title: 'Your laptop', sub: 'code and the CLI', icon: 'screen', tone: 'source', children: [
            { type: 'item', id: 'l-cli', title: 'databricks CLI', sub: 'REST calls', icon: 'terminal' },
            { type: 'item', id: 'l-connect', title: 'Databricks Connect', sub: 'Spark calls, run remotely', icon: 'spark' },
          ],
        },
        {
          type: 'group', id: 'control', badge: 2, title: 'Control plane', sub: 'Databricks’ account: decides, never computes', icon: 'databricks', tone: 'infra', children: [
            { type: 'item', id: 'c-api', title: 'web app and REST API', sub: 'every command lands here', icon: 'globe' },
            { type: 'item', id: 'c-uc', title: 'Unity Catalog metastore', sub: 'names, grants, lineage', icon: 'lock' },
            { type: 'item', id: 'c-jobs', title: 'jobs and pipelines', sub: 'schedules and runs them', icon: 'clock' },
          ],
        },
        {
          type: 'group', id: 'compute', badge: 3, title: 'Serverless compute plane', sub: 'Databricks’ account: starts in seconds', icon: 'cpu', tone: 'ingest', children: [
            { type: 'item', id: 'x-wh', title: `${warehouse[1]}`, sub: `a ${warehouse[2]} SQL warehouse: SQL only`, icon: 'database' },
            { type: 'item', id: 'x-nb', title: 'serverless compute', sub: 'notebooks, jobs, Connect: Python and SQL', icon: 'cpu' },
          ],
        },
        {
          type: 'group', id: 'storage', badge: 4, title: 'Storage', sub: 'object storage: the data', icon: 'cloud', tone: 'store', children: [
            { type: 'item', id: 's-managed', title: 'managed tables, volumes', sub: 'Free Edition: the workspace’s default storage', icon: 'layers' },
            { type: 'item', id: 's-classic', title: 'your own cloud account', sub: 'classic compute and storage: not on Free Edition', icon: 'server' },
          ],
        },
      ],
    },
    {
      type: 'group', id: 'proof', bare: true, dir: 'row', children: [
        {
          type: 'group', id: 'lab', title: 'Asked from the laptop', icon: 'terminal', tone: 'source', children: [
            { type: 'code', id: 'lab-describe', terminal: true, filename: 'databricks auth describe (excerpt)', code: excerpt.join('\n') },
            { type: 'code', id: 'lab-warehouses', terminal: true, filename: 'databricks warehouses list', code: outputOf(s2, 'databricks warehouses list') },
          ],
        },
        {
          type: 'group', id: 'tiers', title: 'What this course can show', icon: 'check', tone: 'neutral', children: [
            {
              type: 'table', id: 'tier', columns: ['', 'here'], rows: [
                { id: 't-run', cells: ['serverless compute, SQL warehouse', 'run, every frame'], tone: 'ingest' },
                { id: 't-uc', cells: ['Unity Catalog, jobs, pipelines', 'run'], tone: 'ingest' },
                { id: 't-classic', cells: ['classic clusters, your own storage', 'documented only'] },
              ],
            },
          ],
        },
      ],
    },
  ],
  edges: [
    { from: 'laptop', to: 'control', label: 'HTTPS' },
    { from: 'control', to: 'compute', label: 'starts' },
    { from: 'compute', to: 'storage', label: 'reads, writes' },
  ],
}

// §3 — Databricks Connect: the Spark API, run on serverless.
const hello = outputOf(s3, 'python -m globalbank.hello')
const sparkVersion = hello.match(/Spark (\S+) on serverless/)![1]
const defaultCatalog = hello.match(/in catalog (\S+)/)![1]
const startConnect: SceneModel = ideFrame2({
  model: 'The plan goes up; the rows come back',
  tree: explorer({ files: [...VENV, ...PKG, 'globalbank/hello.py', 'README.md', 'requirements.txt'],
    mark: { ...BASE_MARK, 'globalbank/': 'new', 'requirements.txt': 'new', 'globalbank/session.py': 'active' }, note: BASE_NOTE }),
  editor: { file: 'globalbank/session.py', code: sessionPy, highlight: [lineOf(sessionPy, '.serverless()')] },
  session: s3,
  side: [
    {
      type: 'group', id: 'flow', title: 'python -m globalbank.hello', icon: 'spark', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'f-code', title: 'spark.range(3).show()', sub: 'the PySpark API you know', icon: 'code' },
        { type: 'item', id: 'f-client', title: 'Databricks Connect', sub: 'a Spark Connect client: sends the plan', icon: 'network' },
        { type: 'item', id: 'f-server', title: 'serverless compute', sub: `Spark ${sparkVersion}: runs it, in ${defaultCatalog}`, icon: 'cpu' },
        { type: 'item', id: 'f-back', title: 'rows, back to the laptop', sub: 'only the result crosses', icon: 'table' },
      ],
    },
    {
      type: 'table', id: 'where', title: 'What ran where', tone: 'ingest', columns: ['line', 'ran on'], rows: [
        { id: 'r-sql', cells: ['current_user() …', 'workspace'], tone: 'ingest' },
        { id: 'r-range', cells: ['spark.range(3)', 'workspace'], tone: 'ingest' },
        { id: 'r-print', cells: ['print(…)', 'laptop'] },
      ],
    },
  ],
  edges: [
    { from: 'f-code', to: 'f-client' },
    { from: 'f-client', to: 'f-server', label: 'gRPC' },
    { from: 'f-server', to: 'f-back' },
  ],
})

// §4 — the catalog: one schema per medallion layer, and a volume.
const out4 = outputOf(s4, 'python -m globalbank.catalog')
const schemas = out4.match(/^schemas: (.*)$/m)![1].split(', ')
const volume = out4.match(/^volume:\s+(\S+)$/m)![1]
const layers = ['landing', 'bronze', 'silver', 'gold']
const startCatalog: SceneModel = ideFrame2({
  model: 'catalog.schema.object',
  tree: explorer({ files: [...VENV, ...PKG, 'globalbank/catalog.py', 'globalbank/hello.py', 'README.md', 'requirements.txt'],
    mark: { ...BASE_MARK, 'globalbank/catalog.py': 'active' }, note: BASE_NOTE }),
  editor: { file: 'globalbank/catalog.py', code: catalogPy, highlight: linesFrom(catalogPy, 'def create', "landing.{volume}')") },
  session: s4,
  side: [
    { type: 'item', id: 'cat', title: 'globalbank_dev', sub: 'a catalog: a name’s first part', icon: 'database', tone: 'ingest' },
    {
      type: 'table', id: 'schemas', title: 'its schemas', tone: 'ingest', columns: ['schema', 'holds'],
      rows: schemas.map((s) => ({
        id: `sc-${s}`, cells: [s, layers.includes(s) ? `the ${s} layer` : 'by Databricks'], tone: layers.includes(s) ? 'ingest' as const : undefined,
      })),
    },
    { type: 'item', id: 'vol', title: 'a volume: files, governed', sub: volume.replace('/Volumes/globalbank_dev/', '/Volumes/…/'), icon: 'folder', tone: 'source' },
    {
      type: 'table', id: 'names', title: 'Three-part names', tone: 'store', columns: ['catalog', 'schema', 'object'], rows: [
        { id: 'n-table', cells: ['…_dev', 'bronze', 'card_auths: table'] },
        { id: 'n-volume', cells: ['…_dev', 'landing', 'card_auths: volume'] },
      ],
    },
  ],
  edges: [{ from: 'cat', to: 'schemas' }, { from: 'schemas', to: 'vol', label: 'landing holds' }],
})

// §5 — land the first files: generated on the laptop, copied into the volume as they are.
const copied = outputOf(s5, 'bash land.sh 2026-10-01 | wc -l').trim()
const firstFiles = outputOf(s5, 'ls landing/card_auths/2026-10-01 | head -3').split('\n').filter(Boolean)
const local = outputOf(s5, 'ls landing/card_auths/2026-10-01 | wc -l').trim()
const remote = outputOf(s5, 'databricks fs ls dbfs:/Volumes/globalbank_dev/landing/card_auths/2026-10-01 | wc -l').trim()
const startLand: SceneModel = ideFrame2({
  model: 'Laptop files into a volume',
  tree: explorer({ files: [...LANDED, ...PKG, 'globalbank/catalog.py', 'globalbank_sim/', 'land.sh', 'README.md', 'requirements.txt'],
    mark: { ...BASE_MARK, 'globalbank_sim/': 'new', 'land.sh': 'active' }, note: { ...BASE_NOTE, 'landing/': `${local} files, 1 October` } }),
  editor: { file: 'land.sh', code: landSh, lang: 'shell', highlight: linesFrom(landSh, 'python -m globalbank_sim', 'databricks fs cp') },
  session: s5,
  side: [
    {
      type: 'group', id: 'trip', title: 'One day, landed', icon: 'card', tone: 'source', ...FILL, children: [
        { type: 'item', id: 't-gen', title: 'globalbank_sim', sub: 'the card processor, simulated', icon: 'factory' },
        { type: 'item', id: 't-local', title: 'landing/', sub: `${local} files on the laptop`, icon: 'folder' },
        { type: 'item', id: 't-vol', title: 'the card_auths volume', sub: `${remote} files, in a folder per day`, icon: 'cloud' },
      ],
    },
    {
      type: 'table', id: 'files', title: 'A file every 15 minutes', tone: 'source', columns: ['file', 'holds'], rows: [
        ...firstFiles.map((f) => ({ id: `f-${f}`, cells: [f, 'JSON lines'] })),
        { id: 'f-count', cells: [`${copied} copied`, 'by fs cp'], tone: 'ingest' as const },
      ],
    },
  ],
  edges: [
    { from: 't-gen', to: 't-local', label: 'write' },
    { from: 't-local', to: 't-vol', label: 'fs cp' },
  ],
})

// §6 — the first table: a managed Delta table in bronze, version 0.
const out6 = outputOf(s6, 'python -m globalbank.first_table')
const [, rows, table] = out6.match(/^(\d+) rows in (\S+)$/m)!
const amountType = out6.match(/^amount is (\w+)$/m)![1]
const tableInfo = outputOf(s6, `databricks tables get globalbank_dev.bronze.card_auths | grep -E '"(table_type|data_source_format)"'`)
const fmt = tableInfo.match(/"data_source_format": "(\w+)"/)![1]
const kind = tableInfo.match(/"table_type": "(\w+)"/)![1]
const startFirstTable: SceneModel = ideFrame2({
  model: 'Files in, a Delta table out',
  tree: explorer({ files: [...LANDED, ...PKG, 'globalbank/catalog.py', 'globalbank/first_table.py', 'globalbank_sim/', 'land.sh', 'README.md'],
    mark: { ...BASE_MARK, 'globalbank/first_table.py': 'active' }, note: BASE_NOTE }),
  editor: { file: 'globalbank/first_table.py', code: firstTable, highlight: linesFrom(firstTable, 'spark.read.json', 'saveAsTable') },
  session: s6,
  side: [
    {
      type: 'group', id: 'made', title: table, sub: `${kind.toLowerCase()} ${fmt}: bronze’s first table`, icon: 'layers', tone: 'infra', ...FILL, children: [
        { type: 'item', id: 'm-files', title: 'the volume’s JSON files', sub: 'landing, untouched', icon: 'folder' },
        { type: 'item', id: 'm-delta', title: `${rows} rows, as Delta`, sub: 'Parquet data files + a transaction log', icon: 'layers' },
      ],
    },
    {
      type: 'table', id: 'types', title: 'What inference chose', tone: 'consume', columns: ['column', 'type', 'for money'], rows: [
        { id: 'ty-amount', cells: ['amount', amountType, 'wrong: binary'], tone: 'consume' },
      ],
    },
  ],
  edges: [{ from: 'm-files', to: 'm-delta', label: 'read.json → saveAsTable' }],
})

export const startScenes: Record<string, SceneModel> = {
  'start-cli': startCli,
  'start-where': startWhere,
  'start-connect': startConnect,
  'start-catalog': startCatalog,
  'start-land': startLand,
  'start-first-table': startFirstTable,
}
