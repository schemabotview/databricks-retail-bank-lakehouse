import type { Group, Item, SceneModel, SceneNode, Tone } from '@graphlearning/graphl-flow'

// The app map: what `globalbank` is made of, laid out as its medallion, each part tagged with the
// course that builds it. One scene function, several uses: 1.4 (the plan), 7.x (the pipeline built)
// and 12.5 (everything, with the finished bank's real output). With `built`, a part whose course is
// later is drawn muted; without it, the whole plan is drawn lit.
export interface MapPart { id: string; title: string; sub: string; icon: string; course: number }

export const SOURCES: MapPart[] = [
  { id: 'm-src-cards', title: 'card processor', sub: 'authorizations, every 15 min', icon: 'card', course: 3 },
  { id: 'm-src-clearing', title: 'card scheme', sub: 'clearing, 1–3 days later', icon: 'building', course: 4 },
  { id: 'm-src-core', title: 'core banking', sub: 'customer and account changes', icon: 'database', course: 5 },
]
export const LAYERS: { id: string; title: string; promise: string; tone: Tone; parts: MapPart[] }[] = [
  {
    id: 'm-bronze', title: 'bronze', promise: 'complete', tone: 'infra', parts: [
      { id: 'm-b-auths', title: 'card_auths', sub: 'Auto Loader, every file once', icon: 'stream', course: 3 },
      { id: 'm-b-cdc', title: 'core_cdc, settlements', sub: 'as received', icon: 'file', course: 4 },
    ],
  },
  {
    id: 'm-silver', title: 'silver', promise: 'correct', tone: 'ingest', parts: [
      { id: 'm-s-txn', title: 'card_transactions', sub: 'settled, constrained', icon: 'check', course: 4 },
      { id: 'm-s-cust', title: 'customers, accounts', sub: 'current and history', icon: 'users', course: 5 },
    ],
  },
  {
    id: 'm-gold', title: 'gold', promise: 'ready', tone: 'store', parts: [
      { id: 'm-g-stmt', title: 'balances, statements', sub: 'and the as-of report', icon: 'table', course: 8 },
      { id: 'm-g-fraud', title: 'fraud_flags', sub: 'scored in minutes', icon: 'shield', course: 9 },
    ],
  },
]
export const CONSUMERS: MapPart[] = [
  { id: 'm-c-finance', title: 'finance, branches', sub: 'a dashboard', icon: 'chart', course: 8 },
  { id: 'm-c-regulator', title: 'the regulator', sub: '"as reported on 31 October"', icon: 'search', course: 8 },
  { id: 'm-c-risk', title: 'risk', sub: 'fraud alerts', icon: 'bell', course: 9 },
]
export const AROUND: MapPart[] = [
  { id: 'm-a-protect', title: 'protect', sub: 'Unity Catalog', icon: 'lock', course: 6 },
  { id: 'm-a-pipeline', title: 'declare', sub: 'Lakeflow pipelines', icon: 'workflow', course: 7 },
  { id: 'm-a-schedule', title: 'schedule', sub: 'Lakeflow Jobs', icon: 'clock', course: 10 },
  { id: 'm-a-ship', title: 'ship', sub: 'bundles, CI', icon: 'package', course: 11 },
  { id: 'm-a-operate', title: 'operate', sub: 'cost, speed', icon: 'activity', course: 12 },
]

const lit = (p: MapPart, built?: number) => built === undefined || p.course <= built
const card = (p: MapPart, built?: number, tone?: Tone): Item =>
  ({ type: 'item', id: p.id, title: p.title, sub: `${p.sub} · course ${p.course}`, icon: p.icon, tone: lit(p, built) ? tone : 'neutral' })

export function appMap({ title, sub, built, output }: { title: string; sub: string; built?: number; output?: SceneNode }): SceneModel {
  const sources: Group = {
    type: 'group', id: 'm-sources', title: 'Sources', sub: 'files, as the systems send them', icon: 'server', tone: 'source',
    children: SOURCES.map((p) => card(p, built)),
  }
  const landing: Group = {
    type: 'group', id: 'm-landing', title: 'landing', sub: 'Volumes: the files, kept', icon: 'folder', tone: 'source', spread: true,
    children: [{ type: 'item', id: 'm-l-files', title: '/Volumes/…/landing', sub: 'course 2', icon: 'cloud' }],
  }
  // The layers stack (bronze over silver over gold), each holding its parts in a row: a strip of
  // seven columns was 3:1 and shrank every word under the 24px floor.
  const layers: Group = {
    type: 'group', id: 'm-medallion', bare: true, children: LAYERS.map((l) => ({
      type: 'group', id: l.id, title: `${l.title} · ${l.promise}`, icon: 'layers', tone: l.tone, dir: 'row',
      children: l.parts.map((p) => card(p, built, l.tone)),
    })),
  }
  const consumers: Group = {
    type: 'group', id: 'm-consumers', title: 'Consumers', sub: 'read gold only', icon: 'users', tone: 'serve',
    children: output ? [output] : CONSUMERS.map((p) => card(p, built)),
  }
  const around: Group = {
    type: 'group', id: 'm-around', title: 'Around every layer', icon: 'settings', tone: 'neutral', dir: 'row', span: 'all',
    children: AROUND.map((p) => card(p, built, 'infra')),
  }
  return {
    title, sub,
    nodes: [
      { type: 'group', id: 'm-flow', bare: true, dir: 'row', children: [sources, landing, layers, consumers] },
      around,
    ],
    edges: [
      { from: 'm-sources', to: 'm-landing', label: 'land' },
      { from: 'm-landing', to: 'm-bronze' },
      { from: 'm-bronze', to: 'm-silver' },
      { from: 'm-silver', to: 'm-gold' },
      { from: 'm-gold', to: 'm-consumers', label: 'serve' },
    ],
  }
}
