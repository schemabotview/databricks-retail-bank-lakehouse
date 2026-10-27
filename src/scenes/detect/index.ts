import type { SceneModel } from '@graphlearning/graphl-flow'
import { ideFrame, lineOf, linesFrom } from '../ide'
import { outputOf } from '../lab'
import { BASE_MARK, BASE_NOTE, explorer } from '../tree'
import ring1 from '../../../spine/detect/01-card-testing/project/globalbank/ring.py?raw'
import s1 from '../../../spine/detect/01-card-testing/session.txt?raw'
import rules2 from '../../../spine/detect/02-rules/project/sql/fraud/velocity.sql?raw'
import s2 from '../../../spine/detect/02-rules/session.txt?raw'
import stream3 from '../../../spine/detect/03-streaming-rule/project/globalbank/stream.py?raw'
import s3 from '../../../spine/detect/03-streaming-rule/session.txt?raw'
import features4 from '../../../spine/detect/04-features/project/globalbank/features.py?raw'
import s4 from '../../../spine/detect/04-features/session.txt?raw'
import train5 from '../../../spine/detect/05-mlflow/project/globalbank/train.py?raw'
import s5 from '../../../spine/detect/05-mlflow/session.txt?raw'
import registry6 from '../../../spine/detect/06-registry/project/globalbank/registry.py?raw'
import s6 from '../../../spine/detect/06-registry/session.txt?raw'
import score7 from '../../../spine/detect/07-score/project/globalbank/score.py?raw'
import s7 from '../../../spine/detect/07-score/session.txt?raw'
import tradeoff8 from '../../../spine/detect/08-tradeoff/project/globalbank/tradeoff.py?raw'
import s8 from '../../../spine/detect/08-tradeoff/session.txt?raw'

// Course 9 — Catch card fraud (silver → ml → gold). Every frame is a workspace run (spine/detect/):
// the rule and features run on serverless; the model is trained and scored on the laptop (sklearn),
// tracked and registered in the workspace (MLflow, Unity Catalog). Labels: September's chargebacks.

const all = (text: string, re: RegExp) => [...text.matchAll(re)]
const num = (s: string) => Number(s.replace(/,/g, ''))
const FILL = { spread: true, minH: 520 } as const
const tree = (files: string[], active: string, isNew: string[] = []) =>
  explorer({
    files: ['.venv/', 'landing/', ...files.filter((f) => !f.startsWith('globalbank/')), 'globalbank/session.py', ...files.filter((f) => f.startsWith('globalbank/')), 'pipelines/'],
    mark: { ...BASE_MARK, [active]: 'active', ...Object.fromEntries(isNew.map((f) => [f, 'new' as const])) },
    note: BASE_NOTE,
  })
const grid = (out: string) => {
  const lines = out.split('\n').filter((l) => l.trim())
  const split = (l: string) => l.trim().split(/\s{2,}/)
  return { columns: split(lines[0]), rows: lines.slice(1).map(split) }
}

// §1 — what card testing looks like: the 22 October ring.
const out1 = outputOf(s1, 'python -m globalbank.ring 2026-10-22')
const cards1 = all(out1, /^\s+(K\d+)\s+(\d+) auths in\s+(\d+) min\s+([\d.]+) EUR\s+(\d+) declined\s+(\d+) merchants$/gm)
  .map((m) => ({ card: m[1], auths: Number(m[2]), mins: Number(m[3]), eur: m[4], declined: Number(m[5]), merchants: Number(m[6]) }))
const one1 = out1.match(/^(K\d+): (.*)$/m)!
const times1 = one1[2].split(' ').map((t) => { const [hm, a] = t.split('/'); const [h, m] = hm.split(':').map(Number); return { at: h * 60 + m, amount: Number(a) } })
const t0 = times1[0].at
const ring1Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/ring.py'], 'globalbank/ring.py', ['globalbank/ring.py']),
  editor: { file: 'globalbank/ring.py', code: ring1, highlight: linesFrom(ring1, "WHERE to_date(auth_ts) = '{day}' AND hour(auth_ts) < 5", 'GROUP BY card_id HAVING count(*) > 3') },
  session: s1,
  side: [
    {
      type: 'plot', id: 'one', compact: true, title: `${one1[1]}: each authorization, minutes after the first, EUR`,
      x: { labels: times1.map((t) => String(t.at - t0)) }, y: { min: 0, max: 2.5, step: 0.5 },
      series: [{ kind: 'bar', points: times1.map((t, i) => [i, t.amount] as [number, number]), tone: 'consume' }],
    },
    {
      type: 'table', id: 'cards', title: `${cards1.length} cards, before 05:00`, tone: 'consume', columns: ['card', 'auths', 'minutes', 'EUR', 'declined'],
      rows: cards1.map((c) => ({ id: `c-${c.card}`, cells: [c.card, String(c.auths), String(c.mins), c.eur, String(c.declined)], tone: 'consume' as const })),
    },
  ],
})

// §2 — rules first: more than 5 authorizations in 10 minutes, checked against the chargebacks.
const out2 = grid(outputOf(s2, 'python -m globalbank.warehouse sql/fraud/velocity.sql'))
const rules2Scene: SceneModel = ideFrame({
  tree: tree(['sql/fraud/velocity.sql', 'globalbank/ring.py', 'globalbank/warehouse.py'], 'sql/fraud/velocity.sql', ['sql/fraud/velocity.sql']),
  editor: { file: 'sql/fraud/velocity.sql', code: rules2, lang: 'sql', highlight: linesFrom(rules2, 'count(*) OVER (PARTITION BY card_id ORDER BY auth_ts', 'AND CURRENT ROW) AS auths_10m') },
  session: s2,
  side: [
    {
      type: 'table', id: 'days', title: 'The rule, day by day', tone: 'consume', columns: out2.columns,
      rows: out2.rows.map((r) => ({ id: `d-${r[0]}`, cells: r, tone: num(r[3]) > 0 ? 'consume' as const : undefined })),
    },
    {
      type: 'group', id: 'how', title: 'A window per authorization', icon: 'clock', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'h-row', title: 'one authorization', sub: 'card K…, at 02:14', icon: 'card' },
        { type: 'item', id: 'h-win', title: 'the 10 minutes before it', sub: 'same card: RANGE BETWEEN INTERVAL', icon: 'clock' },
        { type: 'item', id: 'h-flag', title: 'more than 5: flagged', sub: 'checked against chargebacks', icon: 'bell' },
      ],
    },
  ],
  edges: [
    { from: 'h-row', to: 'h-win' },
    { from: 'h-win', to: 'h-flag', label: '> 5' },
  ],
})

// §3 — a streaming rule: windows and a watermark over bronze.
const flags3 = all(outputOf(s3, 'python -m globalbank.stream'), /^(\d+ \w+ \d\d:\d\d)-(\d\d:\d\d)\s+(K\d+)\s+(\d+) auths\s+([\d.]+) EUR$/gm)
  .map((m) => ({ from: m[1], to: m[2], card: m[3], auths: m[4], eur: m[5] }))
const stream3Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/stream.py', 'globalbank/ring.py'], 'globalbank/stream.py', ['globalbank/stream.py']),
  editor: { file: 'globalbank/stream.py', code: stream3, highlight: linesFrom(stream3, ".withWatermark('auth_ts', '30 minutes')", ".where('auths > 5'))") },
  session: s3,
  side: [
    {
      type: 'table', id: 'flags', title: `gold.fraud_flags: ${flags3.length} windows`, tone: 'consume', columns: ['window', 'card', 'auths', 'EUR'],
      rows: flags3.map((f, i) => ({ id: `f-${i}`, cells: [`${f.from}–${f.to}`, f.card, f.auths, f.eur], tone: 'consume' as const })),
    },
    {
      type: 'group', id: 'wm', title: 'Window and watermark', icon: 'stream', tone: 'ingest', ...FILL, children: [
        { type: 'item', id: 'w-win', title: '10-minute windows, every 5 minutes', sub: 'per card: count and total', icon: 'clock' },
        { type: 'item', id: 'w-wm', title: 'watermark: 30 minutes', sub: 'how late a row may still arrive', icon: 'filter' },
        { type: 'item', id: 'w-out', title: 'a window closes: append its flags', sub: 'once, never revised', icon: 'bell' },
      ],
    },
  ],
  edges: [
    { from: 'w-win', to: 'w-wm' },
    { from: 'w-wm', to: 'w-out', label: 'passes the window' },
  ],
})

// §4 — features in Unity Catalog.
const out4 = outputOf(s4, 'python -m globalbank.features')
const rows4 = out4.match(/: ([\d,]+) rows/)![1]
const days4 = all(out4, /^\|(\S+)\|\s*(\d+)\|\s*(\d+)\|\s*([\d.]+)\|$/gm).map((m) => m.slice(1, 5))
const features4Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/features.py', 'globalbank/stream.py'], 'globalbank/features.py', ['globalbank/features.py']),
  editor: { file: 'globalbank/features.py', code: features4, highlight: linesFrom(features4, 'count(*) OVER (PARTITION BY card_id ORDER BY auth_ts', 'AS INT) AS fraud') },
  session: s4,
  side: [
    {
      type: 'table', id: 'features', title: 'ml.card_features: one row per authorization', tone: 'store', columns: ['feature', 'what the model sees'], rows: [
        { id: 'x-vel', cells: ['auths_10m', 'the card’s authorizations in 10 minutes'], tone: 'store' },
        { id: 'x-on', cells: ['online', 'card not present'] },
        { id: 'x-tiny', cells: ['tiny_amount', 'under 2 EUR: a test charge'] },
        { id: 'x-night', cells: ['night', 'before 05:00'] },
        { id: 'x-fraud', cells: ['fraud', 'the label: a chargeback (September only)'], tone: 'consume' },
      ],
    },
    {
      type: 'table', id: 'days', title: `${rows4} rows, by day`, tone: 'store', columns: ['day', 'auths', 'fraud', 'avg auths_10m'],
      rows: days4.map((d) => ({ id: `d-${d[0]}`, cells: d, tone: Number(d[2]) > 0 ? 'consume' as const : undefined })),
    },
  ],
})

// §5 — MLflow tracking: train on 12 September, test on 26 September.
const out5 = outputOf(s5, 'python -m globalbank.train')
const sizes5 = out5.match(/trained on ([\d,]+) rows \((\d+) fraud\), tested on ([\d,]+) \((\d+) fraud\)/)!
const metric5 = (k: string) => out5.match(new RegExp(`^\\s+${k}\\s+([\\d.]+)$`, 'm'))![1]
const weights5 = all(out5.match(/weights\s+(.*)$/m)![1], /(\w+) ([+-][\d.]+)/g).map((m) => ({ x: m[1], w: Number(m[2]) }))
const train5Scene: SceneModel = ideFrame({
  tree: tree(['requirements.txt', 'globalbank/features.py', 'globalbank/train.py'], 'globalbank/train.py', ['globalbank/train.py']),
  editor: { file: 'globalbank/train.py', code: train5, show: [[1, 2], [lineOf(train5, "mlflow.set_experiment"), lineOf(train5, 'registered_model_name=MODEL)')]], highlight: linesFrom(train5, "with mlflow.start_run(run_name='logreg-sep12') as run:", 'mlflow.log_metrics(metrics)') },
  session: s5,
  side: [
    {
      type: 'group', id: 'run', title: 'One MLflow run, in the workspace', icon: 'activity', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'r-params', title: 'params', sub: `C, features, ${sizes5[1]} train rows, ${sizes5[3]} test rows`, icon: 'settings' },
        { type: 'item', id: 'r-metrics', title: `precision ${metric5('precision')}, recall ${metric5('recall')}`, sub: 'on 26 September: data it never saw', icon: 'chart' },
        { type: 'item', id: 'r-model', title: 'the model', sub: 'logged, and registered in Unity Catalog', icon: 'package' },
      ],
    },
    {
      type: 'plot', id: 'weights', compact: true, title: 'What it learned: a weight per feature',
      x: { labels: weights5.map((w) => w.x) }, y: { min: Math.min(0, Math.floor(Math.min(...weights5.map((w) => w.w)))), max: Math.ceil(Math.max(...weights5.map((w) => w.w))), step: 1 },
      series: [{ kind: 'bar', points: weights5.map((w, i) => [i, w.w] as [number, number]), tone: 'store' }],
    },
  ],
  edges: [
    { from: 'r-params', to: 'r-metrics' },
    { from: 'r-metrics', to: 'r-model' },
  ],
})

// §6 — a model in Unity Catalog: versions and the champion alias.
const blocks6 = s6.split(/^\$ /m).slice(1)
const versions6 = (b: string) => all(b, /^\s+version (\d+)\s+(\w+)\s*(\w*)$/gm).map((m) => ({ v: m[1], status: m[2], alias: m[3] }))
const before6 = versions6(blocks6[0])
const after6 = versions6(blocks6[1])
const registry6Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/registry.py', 'globalbank/train.py'], 'globalbank/registry.py', ['globalbank/registry.py']),
  editor: { file: 'globalbank/registry.py', code: registry6, highlight: [lineOf(registry6, "client.set_registered_model_alias(MODEL, 'champion', sys.argv[2])")] },
  session: s6,
  side: [
    {
      type: 'table', id: 'versions', title: 'globalbank_dev.ml.card_fraud', tone: 'store', columns: ['version', 'status', 'before', 'after'],
      rows: after6.map((a, i) => ({ id: `v-${a.v}`, cells: [a.v, a.status, before6[i]?.alias || '—', a.alias || '—'], tone: a.alias ? 'store' as const : undefined })),
    },
    {
      type: 'group', id: 'alias', title: 'models:/…/card_fraud@champion', icon: 'package', tone: 'store', ...FILL, children: [
        { type: 'item', id: 'a-name', title: 'catalog.schema.model', sub: 'governed like a table: grants, lineage', icon: 'lock' },
        { type: 'item', id: 'a-ver', title: 'versions', sub: 'every registration, kept', icon: 'layers' },
        { type: 'item', id: 'a-alias', title: '@champion', sub: 'what scoring loads: move it, not the code', icon: 'check' },
      ],
    },
  ],
  edges: [
    { from: 'a-name', to: 'a-ver' },
    { from: 'a-ver', to: 'a-alias' },
  ],
})

// §7 — score a day with the champion.
const out7 = outputOf(s7, 'python -m globalbank.score 2026-10-22 0.9')
const head7 = out7.split('\n')[0]
const flagged7 = all(out7, /^\s+(K\d+)\s+(\d+) auths\s+first (\d\d:\d\d)\s+score ([\d.]+)$/gm).map((m) => m.slice(1, 5))
const score7Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/registry.py', 'globalbank/score.py', 'globalbank/train.py'], 'globalbank/score.py', ['globalbank/score.py']),
  editor: { file: 'globalbank/score.py', code: score7, highlight: linesFrom(score7, "CHAMPION = 'models:/globalbank_dev.ml.card_fraud@champion'", "batch['score'] = model.predict_proba(batch[X])[:, 1]") },
  session: s7,
  side: [
    {
      type: 'group', id: 'path', title: head7, icon: 'shield', tone: 'consume', ...FILL, children: [
        { type: 'item', id: 'p-feat', title: 'ml.card_features, 22 October', sub: 'pulled by Databricks Connect', icon: 'table' },
        { type: 'item', id: 'p-model', title: 'card_fraud@champion', sub: 'loaded from Unity Catalog', icon: 'package' },
        { type: 'item', id: 'p-flags', title: 'gold.fraud_flags', sub: 'score ≥ 0.9: appended', icon: 'bell' },
      ],
    },
    {
      type: 'table', id: 'cards', title: 'Flagged cards', tone: 'consume', columns: ['card', 'auths', 'first', 'score'],
      rows: flagged7.map((f) => ({ id: `k-${f[0]}`, cells: f, tone: 'consume' as const })),
    },
  ],
  edges: [
    { from: 'p-feat', to: 'p-model' },
    { from: 'p-model', to: 'p-flags' },
  ],
})

// §8 — precision, recall, money: thresholds against the analysts' queue.
const out8 = outputOf(s8, 'python -m globalbank.tradeoff')
const head8 = out8.split('\n')[0]
const rows8 = all(out8, /^\s*([\d.]+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)$/gm).map((m) => m.slice(1, 7))
const tradeoff8Scene: SceneModel = ideFrame({
  tree: tree(['globalbank/score.py', 'globalbank/tradeoff.py'], 'globalbank/tradeoff.py', ['globalbank/tradeoff.py']),
  editor: { file: 'globalbank/tradeoff.py', code: tradeoff8, highlight: linesFrom(tradeoff8, 'for t in (0.5, 0.7, 0.9, 0.97, 0.99):', "f'  {len(hit) / len(fraud):>6.2f}  {hit.amount.sum():>16}')") },
  session: s8,
  side: [
    {
      type: 'plot', id: 'curve', compact: true, title: 'Precision and recall by threshold, 26 September',
      x: { labels: rows8.map((r) => r[0]) }, y: { min: 0, max: 1, step: 0.25 },
      series: [
        { kind: 'line', label: 'precision', points: rows8.map((r, i) => [i, Number(r[3])] as [number, number]), tone: 'store' },
        { kind: 'line', label: 'recall', points: rows8.map((r, i) => [i, Number(r[4])] as [number, number]), tone: 'consume' },
      ],
    },
    {
      type: 'table', id: 'queue', title: head8, tone: 'consume', columns: ['threshold', 'queue', 'caught', 'EUR caught'],
      rows: rows8.map((r) => ({ id: `t-${r[0]}`, cells: [r[0], r[1], r[2], r[5]] })),
    },
  ],
})

export const detectScenes: Record<string, SceneModel> = {
  'detect-card-testing': ring1Scene,
  'detect-rules': rules2Scene,
  'detect-streaming-rule': stream3Scene,
  'detect-features': features4Scene,
  'detect-mlflow': train5Scene,
  'detect-registry': registry6Scene,
  'detect-score': score7Scene,
  'detect-tradeoff': tradeoff8Scene,
}
