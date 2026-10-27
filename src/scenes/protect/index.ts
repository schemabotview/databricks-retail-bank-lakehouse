import type { SceneModel } from '@graphlearning/graphl-flow'
import { view } from '../fold'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import s1 from '../../../spine/protect/01-unity-catalog/session.txt?raw'
import grants2 from '../../../spine/protect/02-grants/project/governance/grants.sql?raw'
import s2 from '../../../spine/protect/02-grants/session.txt?raw'
import masks3 from '../../../spine/protect/03-masks/project/governance/masks.sql?raw'
import s3 from '../../../spine/protect/03-masks/session.txt?raw'
import filters4 from '../../../spine/protect/04-row-filters/project/governance/filters.sql?raw'
import s4 from '../../../spine/protect/04-row-filters/session.txt?raw'
import tags5 from '../../../spine/protect/05-tags/project/governance/tags.sql?raw'
import s5 from '../../../spine/protect/05-tags/session.txt?raw'
import lineage6 from '../../../spine/protect/06-lineage/project/globalbank/lineage.py?raw'
import s6 from '../../../spine/protect/06-lineage/session.txt?raw'
import audit7 from '../../../spine/protect/07-audit/project/globalbank/audit.py?raw'
import s7 from '../../../spine/protect/07-audit/session.txt?raw'
import erase8 from '../../../spine/protect/08-erasure/project/globalbank/erase.py?raw'
import s8 from '../../../spine/protect/08-erasure/session.txt?raw'

// Course 6 — Protect customers' data (governance by layer). Every IDE frame is a workspace run
// (spine/protect/). Free Edition has no account groups, so 6.2's grants are refused there (run) and
// the access matrix beside them is documented; masks and filters read a role-mapping table, so
// one user switching roles shows two readers.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const num = (s: string) => Number(s.replace(/,/g, ''))
const fmt = (n: number) => n.toLocaleString('en')
const FILL = { spread: true, minH: 520 } as const
const PKG = ['globalbank/__init__.py', 'globalbank/session.py', 'globalbank/cdc.py']
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...files.filter((f) => f.startsWith('governance/')), ...PKG, ...files.filter((f) => !f.startsWith('governance/')), 'land.sh'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const GOV = 'python -m globalbank.govern governance/'
const govern = (out: string) => ({
  lines: all(out, /^(ok|no)\s+(.+)$/gm).map((m) => ({ ok: m[1] === 'ok', what: m[2] })),
  summary: out.split('\n').at(-1)!,
})

// §1 — ◆ full scene: Unity Catalog's object model, with the lab's real answers.
const uc = outputOf(s1, 'python -m globalbank.uc')
const catalogs1 = uc.match(/^catalogs:\s+(.+)$/m)![1]
const owner1 = uc.match(/^owner:\s+(.+)$/m)![1]
const schemas1 = all(uc, /^\s+(\w+)\s+(\d+) tables, (\d+) volumes$/gm).map((m) => ({ schema: m[1], tables: Number(m[2]), volumes: Number(m[3]) }))
const ROLE: Record<string, string> = {
  landing: 'the generator writes; bronze ingest reads', bronze: 'engineers', silver: 'engineers, risk',
  gold: 'finance, branches, the regulator', governance: 'masks, filters, the roles table', vault: 'PII, kept apart (6.8)',
}
const unityCatalog1: SceneModel = {
  title: 'Unity Catalog',
  sub: 'one namespace for every table, volume and function, and one place to say who may read them',
  nodes: [
    {
      type: 'group', id: 'model', bare: true, dir: 'row', children: [
        {
          type: 'group', id: 'metastore', badge: 1, title: 'Metastore', sub: 'one per region: Free Edition has one', icon: 'lock', tone: 'infra', children: [
            { type: 'item', id: 'ms-cat', title: `catalogs: ${catalogs1}`, sub: 'filtered to ours: the owner has others', icon: 'database' },
            { type: 'item', id: 'ms-owner', title: `owner: ${owner1}`, sub: 'owns, so may grant', icon: 'user' },
          ],
        },
        {
          type: 'group', id: 'schemas', badge: 2, title: 'globalbank_dev', sub: 'catalog → schema → object', icon: 'database', tone: 'ingest', children: [
            {
              type: 'table', id: 'layers', columns: ['schema', 'tables', 'volumes', 'for'],
              rows: schemas1.map((s) => ({ id: `s-${s.schema}`, cells: [s.schema, String(s.tables), String(s.volumes), ROLE[s.schema] ?? ''], tone: s.tables ? 'ingest' as const : undefined })),
            },
          ],
        },
        {
          type: 'group', id: 'rules', badge: 3, title: 'What it governs', sub: 'every read goes through it', icon: 'shield', tone: 'store', children: [
            { type: 'item', id: 'r-grant', title: 'grants', sub: 'who may use a schema, read a table (6.2)', icon: 'key' },
            { type: 'item', id: 'r-mask', title: 'masks and row filters', sub: 'what each reader sees (6.3, 6.4)', icon: 'filter' },
            { type: 'item', id: 'r-tags', title: 'tags, lineage, audit', sub: 'what it is, where it came from, who read it', icon: 'search' },
          ],
        },
      ],
    },
    {
      type: 'group', id: 'lab', title: 'python -m globalbank.uc, on the workspace', icon: 'terminal', tone: 'source', children: [
        { type: 'code', id: 'lab-out', terminal: true, filename: 'terminal — globalbank', code: uc },
      ],
    },
  ],
  edges: [
    { from: 'metastore', to: 'schemas', label: 'holds' },
    { from: 'schemas', to: 'rules', label: 'governed by' },
  ],
}

// §2 — grants by layer: written as code; refused on Free Edition, which has no account groups.
const g2 = govern(outputOf(s2, `${GOV}grants.sql`))
const reason2 = g2.summary.split(': ')[1] ?? ''
const grants2Scene: SceneModel = ideFrame({
  tree: tree(['governance/grants.sql', 'globalbank/govern.py'], 'governance/grants.sql', ['governance/grants.sql', 'globalbank/govern.py']),
  editor: { file: 'governance/grants.sql', code: grants2, lang: 'sql', highlight: linesFrom(grants2, 'GRANT USE CATALOG', 'TO `branches`') },
  session: s2,
  side: [
    {
      type: 'table', id: 'matrix', title: 'Who reads which layer (documented)', tone: 'store', columns: ['group', 'bronze', 'silver', 'gold'], rows: [
        { id: 'm-eng', cells: ['engineers', 'read', 'read', ''] },
        { id: 'm-risk', cells: ['risk', '', 'read', ''] },
        { id: 'm-fin', cells: ['finance', '', '', 'read'], tone: 'store' },
        { id: 'm-br', cells: ['branches', '', '', 'read'], tone: 'store' },
      ],
    },
    {
      type: 'group', id: 'why', title: `On Free Edition: ${reason2}`, icon: 'users', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'w-idp', title: 'the bank’s identity provider', sub: 'groups, synced by SCIM to the account', icon: 'building' },
        { type: 'item', id: 'w-acct', title: 'account groups', sub: 'what Unity Catalog grants to', icon: 'users' },
        { type: 'item', id: 'w-fe', title: 'Free Edition: no SCIM, no account console', sub: `${g2.lines.filter((l) => !l.ok).length} of ${g2.lines.length} grants refused`, icon: 'bell' },
      ],
    },
  ],
  edges: [
    { from: 'w-idp', to: 'w-acct', label: 'SCIM' },
    { from: 'w-acct', to: 'w-fe', label: 'missing here' },
  ],
})

// §3 — column masks: one query, two readers (the role-mapping table switches the reader).
const peek = (out: string) => all(out, /^(C\d+)\s+national_id (\S+)\s+iban (\S+)$/gm).map((m) => m.slice(1, 4))
const PEEK = 'python -m globalbank.peek'
const blocks3 = s3.split(/^\$ /m).slice(1)
const peeks3 = blocks3.filter((b) => b.startsWith(PEEK)).map((b) => peek(b))
const role3 = outputOf(s3, 'python -m globalbank.roles risk')
const masks3Scene: SceneModel = ideFrame({
  tree: tree(['governance/grants.sql', 'governance/masks.sql', 'globalbank/peek.py', 'globalbank/roles.py'], 'governance/masks.sql', ['governance/masks.sql', 'globalbank/peek.py', 'globalbank/roles.py']),
  editor: { file: 'governance/masks.sql', code: masks3, lang: 'sql', highlight: linesFrom(masks3, 'RETURN IF(EXISTS', "v, concat('*****', right(v, 3)));") },
  session: s3,
  side: [
    {
      type: 'table', id: 'before', title: 'Read with no role: masked', tone: 'consume', columns: ['customer', 'national_id', 'iban'],
      rows: peeks3[0].map((r) => ({ id: `b-${r[0]}`, cells: r, tone: 'consume' as const })),
    },
    {
      type: 'table', id: 'after', title: `Read as ${role3.split(' reads as ')[1]}: whole`, tone: 'ingest', columns: ['customer', 'national_id', 'iban'],
      rows: peeks3[1].map((r) => ({ id: `a-${r[0]}`, cells: r, tone: 'ingest' as const })),
    },
    {
      type: 'group', id: 'how', title: 'Who decides', icon: 'shield', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'h-q', title: 'the same SELECT', sub: 'peek.py: never changes', icon: 'code' },
        { type: 'item', id: 'h-mask', title: 'unless_risk(national_id)', sub: 'runs on every read of the column', icon: 'filter' },
        { type: 'item', id: 'h-roles', title: 'governance.roles', sub: 'current_user() → risk?', icon: 'table' },
      ],
    },
  ],
  edges: [
    { from: 'h-q', to: 'h-mask' },
    { from: 'h-mask', to: 'h-roles', label: 'asks' },
  ],
})

// §4 — row filters: a branch manager sees their region; risk sees all five.
const blocks4 = s4.split(/^\$ /m).slice(1)
const regions = (b: string) => all(b, /(\w+) ([\d,]+)/g).map((m) => ({ region: m[1], n: num(m[2]) }))
const reg4 = blocks4.filter((b) => b.startsWith('python -m globalbank.regions')).map((b) => regions(b.split('\n').slice(1).join('\n')))
const filters4Scene: SceneModel = ideFrame({
  tree: tree(['governance/filters.sql', 'governance/masks.sql', 'globalbank/regions.py', 'globalbank/roles.py'], 'governance/filters.sql', ['governance/filters.sql', 'globalbank/regions.py']),
  editor: { file: 'governance/filters.sql', code: filters4, lang: 'sql', highlight: linesFrom(filters4, 'RETURN EXISTS', 'SET ROW FILTER') },
  session: s4,
  side: [
    {
      type: 'plot', id: 'rows', compact: true, title: 'Customers per region, by who asks',
      x: { labels: reg4[1].map((r) => r.region) }, y: { min: 0, max: Math.ceil(Math.max(...reg4[1].map((r) => r.n)) / 250) * 250, step: 250 },
      series: [
        { kind: 'bar', label: 'branch, North', points: reg4[1].map((r, i) => [i, reg4[0].find((x) => x.region === r.region)?.n ?? 0]), tone: 'consume' },
        { kind: 'bar', label: 'risk', points: reg4[1].map((r, i) => [i, r.n]), tone: 'ingest' },
      ],
    },
    {
      type: 'table', id: 'who', title: 'One table, two answers', tone: 'store', columns: ['reads as', 'regions', 'customers'], rows: [
        { id: 'w-branch', cells: ['branch, North', String(reg4[0].length), fmt(reg4[0].reduce((a, r) => a + r.n, 0))], tone: 'consume' },
        { id: 'w-risk', cells: ['risk', String(reg4[1].length), fmt(reg4[1].reduce((a, r) => a + r.n, 0))], tone: 'ingest' },
      ],
    },
    { type: 'note', id: 'note', tone: 'store', text: 'The filter runs inside every read of the table, so no query, notebook or dashboard can forget it: one silver table serves every region safely.' },
  ],
})

// §5 — tags: classify PII columns, then find them.
const pii5 = outputOf(s5, 'python -m globalbank.pii')
const tagged5 = all(pii5, /^\s+(\w+)\.(\w+)\.(\w+)\s+(\w+)$/gm).map((m) => ({ schema: m[1], table: m[2], column: m[3], tag: m[4] }))
const tags5Scene: SceneModel = ideFrame({
  tree: tree(['governance/filters.sql', 'governance/masks.sql', 'governance/tags.sql', 'globalbank/pii.py'], 'governance/tags.sql', ['governance/tags.sql', 'globalbank/pii.py']),
  editor: { file: 'governance/tags.sql', code: tags5, lang: 'sql', highlight: [lineOf(tags5, "SET TAGS ('pii' = 'national_id')"), lineOf(tags5, "SET TAGS ('pii' = 'account_number')")] },
  session: s5,
  side: [
    {
      type: 'table', id: 'tagged', title: `${tagged5.length} columns tagged pii`, tone: 'store', columns: ['table', 'column', 'pii'],
      rows: tagged5.map((t) => ({ id: `t-${t.table}-${t.column}`, cells: [`${t.schema}.${t.table}`, t.column, t.tag], tone: ['national_id', 'account_number'].includes(t.tag) ? 'consume' as const : undefined })),
    },
    {
      type: 'group', id: 'audit', title: 'What the tags are for', icon: 'search', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'a-tag', title: 'tag each personal column', sub: 'SET TAGS (\'pii\' = …)', icon: 'file' },
        { type: 'item', id: 'a-find', title: 'find them all, in one query', sub: 'information_schema.column_tags', icon: 'search' },
        { type: 'item', id: 'a-gap', title: 'compare with the masks', sub: 'red: masked; the rest are not yet', icon: 'shield' },
      ],
    },
  ],
  edges: [
    { from: 'a-tag', to: 'a-find' },
    { from: 'a-find', to: 'a-gap' },
  ],
})

// §6 — lineage: what each table was built from, from system.access.table_lineage.
const edges6 = all(outputOf(s6, 'python -m globalbank.lineage'), /^(.+?)\s+-> (\S+)$/gm).map((m) => ({ from: m[1].trim(), to: m[2] }))
const nodes6 = [...new Set(edges6.flatMap((e) => [e.from, e.to]))]
const layer = (n: string) => (n.startsWith('files') ? 'source' : n.startsWith('bronze') ? 'ingest' : n.startsWith('silver') ? 'store' : 'consume') as 'source' | 'ingest' | 'store' | 'consume'
const nid = (n: string) => `n-${n.replace(/[^a-z0-9]+/gi, '-')}`
const lineage6Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/lineage.py', 'globalbank/scd2.py', 'globalbank/ledger.py'], 'globalbank/lineage.py', ['globalbank/lineage.py']),
  editor: { file: 'globalbank/lineage.py', code: lineage6, highlight: linesFrom(lineage6, 'FROM system.access.table_lineage', "event_time > current_timestamp()") },
  session: s6,
  side: [
    {
      type: 'table', id: 'edges', title: 'system.access.table_lineage: what each table read', tone: 'store', columns: ['read', 'to write'],
      rows: edges6.map((e) => ({ id: `e-${nid(e.from)}-${nid(e.to)}`, cells: [e.from, e.to], tone: layer(e.to) })),
    },
    {
      type: 'group', id: 'layers', title: `${nodes6.length} tables and volumes, three layers`, icon: 'workflow', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'l-files', title: 'landing volumes', sub: 'card_auths, core_cdc: files', icon: 'folder', tone: 'source' },
        { type: 'item', id: 'l-bronze', title: 'bronze', sub: 'card_auths, core_cdc', icon: 'layers', tone: 'ingest' },
        { type: 'item', id: 'l-silver', title: 'silver', sub: 'card_transactions, customers, accounts, history', icon: 'layers', tone: 'store' },
      ],
    },
  ],
  edges: [
    { from: 'l-files', to: 'l-bronze', label: 'Auto Loader' },
    { from: 'l-bronze', to: 'l-silver', label: 'MERGE, SCD2' },
  ],
})

// §7 — audit: who touched silver.customers in the last hour.
const out7 = outputOf(s7, 'python -m globalbank.audit')
const rows7 = all(out7, /^\s+(\S+@\S+)\s+(\w+)\s+(\d+)$/gm).map((m) => ({ who: m[1], action: m[2], n: Number(m[3]) }))
const audit7Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/audit.py', 'globalbank/lineage.py', 'globalbank/regions.py'], 'globalbank/audit.py', ['globalbank/audit.py']),
  editor: { file: 'globalbank/audit.py', code: audit7, highlight: linesFrom(audit7, 'FROM system.access.audit', 'event_time > current_timestamp()') },
  session: s7,
  side: [
    {
      type: 'table', id: 'rows', title: 'system.access.audit: silver.customers, the last hour', tone: 'store', columns: ['who', 'action', 'requests'],
      rows: rows7.map((r) => ({ id: `a-${r.action}`, cells: [r.who, r.action, String(r.n)] })),
    },
    {
      type: 'group', id: 'trail', title: 'One read, recorded', icon: 'search', tone: 'store', ...FILL, children: [
        { type: 'item', id: 't-read', title: 'regions.py reads silver.customers', sub: 'through Databricks Connect', icon: 'code' },
        { type: 'item', id: 't-uc', title: 'Unity Catalog checks it', sub: 'and writes an audit event', icon: 'lock' },
        { type: 'item', id: 't-sys', title: 'system.access.audit', sub: 'a table: queried like any other', icon: 'table' },
      ],
    },
  ],
  edges: [
    { from: 't-read', to: 't-uc' },
    { from: 't-uc', to: 't-sys', label: 'minutes later' },
  ],
})

// §8 — erasure vs retention: the vault forgets the person; the facts keep the token.
const out8a = outputOf(s8, 'python -m globalbank.erase')
const who8 = out8a.match(/erase (C\d+)/)![1]
const req8 = out8a.match(/request (\S+):/)![1]
const held8 = all(out8a, /version (\d+) holds them: (\d+) row/g).map((m) => ({ v: m[1], n: m[2] }))
const facts8 = out8a.match(/still holds (\d+) account row/)![1]
const out8b = outputOf(s8, 'python -m globalbank.purge')
const erasure8: SceneModel = ideFrame({
  tree: tree(['globalbank/erase.py', 'globalbank/purge.py', 'globalbank/vault.py'], 'globalbank/erase.py', ['globalbank/erase.py', 'globalbank/purge.py', 'globalbank/vault.py']),
  editor: { file: 'globalbank/erase.py', code: erase8, ...view(erase8, 'path = glob.glob', undefined, 0), highlight: [lineOf(erase8, 'DELETE FROM {VAULT}')] },
  session: s8,
  side: [
    {
      type: 'group', id: 'split', title: `${req8}: erase ${who8}`, icon: 'shield', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'e-facts', title: 'silver.accounts, transactions', sub: `${facts8} account row(s): kept, by customer_id only`, icon: 'layers' },
        { type: 'item', id: 'e-vault', title: 'vault.customer_pii', sub: 'name, national id, address: deleted', icon: 'lock' },
        { type: 'item', id: 'e-files', title: 'old data files', sub: 'REORG rewrites; VACUUM deletes after 7 days', icon: 'file' },
      ],
    },
    {
      type: 'table', id: 'versions', title: 'Time travel still remembers', tone: 'consume', columns: ['version', 'rows for the customer'],
      rows: held8.map((h) => ({ id: `v-${h.v}`, cells: [h.v, h.n], tone: h.n === '1' ? 'consume' as const : 'ingest' as const })),
    },
    { type: 'note', id: 'note', tone: 'consume', text: `${out8b.split('\n')[0]}. Erasure is complete only when the old files are gone. The retention rule here is illustrative, not legal advice.` },
  ],
  edges: [
    { from: 'e-facts', to: 'e-vault', label: 'customer_id' },
    { from: 'e-vault', to: 'e-files', label: 'until purged' },
  ],
})

export const protectScenes: Record<string, SceneModel> = {
  'protect-unity-catalog': unityCatalog1,
  'protect-grants': grants2Scene,
  'protect-masks': masks3Scene,
  'protect-row-filters': filters4Scene,
  'protect-tags': tags5Scene,
  'protect-lineage': lineage6Scene,
  'protect-audit': audit7Scene,
  'protect-erasure': erasure8,
}
