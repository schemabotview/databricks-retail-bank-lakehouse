// IDE frame v2 — the shared frame graphl-flow 0.10+ defines (dev/fixtures/studies/ide-frame.ts) and
// typescript-diagram-engine authors every step section in:
//
//   [explorer] | editor (the rows the terminal leaves)        | side pane, TITLED with the section's
//              | terminal docked under it (its transcript)    | mental model: one diagram, ≤ 1 table
//
// One 1344 × 756 grid at a 1% margin: every v2 frame lands on ONE fit (check-render asserts it, per
// frame kind, while courses migrate from the v1 template in ide.ts). Every column is a FIXED width,
// so content wider than its column overflows (check-render fails it) instead of moving the frame.
// The editor and the terminal share ROWS rows: the terminal takes exactly its transcript's rows (at
// least MIN_TERMINAL), the editor the rest, so no row is empty while code is folded. Only the
// divider between them moves from frame to frame; the explorer and side pane never do (check-render
// holds them to one place). The terminal is 72 columns: the
// recorded sessions (80 columns) are wrapped here, at draw time, so the spine is untouched.
//
// The workbench's id is `ide-bench` (v1's is `workbench`): that is how the checks tell the two apart.
// Ported from python-expense-tracker's frame.ts, via spark-ecommerce-analytics (2026-11-09).
import type { Code, Edge, Group, SceneModel, SceneNode, Tree, TreeEntry } from '@graphlearning/graphl-flow'
import { trim } from './ide'

const ROW = 24
const CHROME = 51
export const GAP = 10
export const FULL_W = 1344
export const FRAME_H = Math.round(FULL_W / (16 / 9))
export const SIDE_W = 434
export const WORK_W = 715
export const EXPLORER_W = FULL_W - (WORK_W + GAP + SIDE_W) - GAP
/** The terminal's width in columns, and the editor's soft-wrap point (it wraps a 72-column line). */
export const COLS = 72
const EDITOR_WRAP = 71

/** Rows the editor and terminal share: (FRAME_H − GAP − two panes' chrome) / ROW. */
export const ROWS = Math.floor((FRAME_H - GAP - 2 * CHROME) / ROW)
/** The fewest rows a terminal gets, however short its transcript. */
export const MIN_TERMINAL = 6
/** The most a terminal can take: the editor keeps at least this many rows. 7 here, not the expense
 *  tracker's 8: a 75-column show() grid wraps every row in two, and 5.6's history needs 19 rows. */
export const MIN_EDITOR = 7
const editorH = (rows: number) => rows * ROW + CHROME

/**
 * A spine session.txt as terminal rows: `$ cmd` and the REPL's `>>>` / `...` lines are commands, a
 * traceback (its header through the exception line that ends it) is marked `! ` as an error, and a
 * line longer than COLS wraps as a real 72-column terminal wraps it — each piece one row.
 */
export function terminal(session: string): string {
  const out: string[] = []
  let inError = false
  for (const line of trim(session).split('\n')) {
    if (line.startsWith('$ ') || line.startsWith('>>> ') || line.startsWith('... ')) inError = false
    else if (!inError && (line === 'Traceback (most recent call last):' || /^ {2}File ".*", line \d+/.test(line))) inError = true
    const rows = line.match(new RegExp(`.{1,${COLS}}`, 'g')) ?? ['']
    if (inError) {
      out.push(...rows.map((row) => `! ${row}`))
      if (/^[A-Za-z_][\w.]*(Error|Exception|Warning|Interrupt|Exit)\b/.test(line)) inError = false
    } else out.push(...rows)
  }
  return out.join('\n')
}

/** Rows one editor line takes. The editor wraps as CSS `pre-wrap` does, at a space when there is
 *  one (a hard cut only inside a longer word), so a line of words can take more rows than its
 *  length / EDITOR_WRAP: a 96-column path (databricks 11.4) took three, and the frame grew a row. */
export function wrappedRows(line: string, width = EDITOR_WRAP): number {
  let rows = 1, rest = line
  while (rest.length > width) {
    const space = rest.lastIndexOf(' ', width) // a space may hang at the end of a row
    const cut = space > 0 && rest.slice(0, space).trim() ? space + 1 : width
    rest = rest.slice(cut)
    rows++
  }
  return rows
}

const rowsOf = (lines: string[], a: number, b: number) =>
  lines.slice(a - 1, b).reduce((n, l) => n + wrappedRows(l), 0)

/** A window of the file around lines first..last that fits `room` editor rows, folds included. */
export function windowFor(code: string, first: number, last: number, room: number): [number, number][] | undefined {
  const lines = trim(code).split('\n')
  if (rowsOf(lines, 1, lines.length) <= room) return undefined
  const fits = (a: number, b: number) => rowsOf(lines, a, b) + (a > 1 ? 1 : 0) + (b < lines.length ? 1 : 0) <= room
  if (!fits(first, last)) throw new Error(`frame.ts: lines ${first}–${last} do not fit ${room} rows`)
  let a = first, b = last
  for (let grew = true; grew;) {
    grew = false
    if (a > 1 && fits(a - 1, b)) { a--; grew = true }
    if (b < lines.length && fits(a, b + 1)) { b++; grew = true }
  }
  return [[a, b]]
}

/** Rows a set of shown ranges takes: each line (wrapped), plus one fold row per skipped run. */
function rowsShown(lines: string[], ranges: [number, number][]): number {
  let rows = 0, next = 1
  for (const [a, b] of ranges) { if (a > next) rows++; rows += rowsOf(lines, a, b); next = b + 1 }
  return rows + (next <= lines.length ? 1 : 0)
}

/** Hand-picked ranges grown, one line at a time, until the editor is full: room is never left empty. */
export function grow(code: string, ranges: [number, number][], room: number): [number, number][] {
  const lines = trim(code).split('\n')
  let r = ranges.map(([a, b]) => [a, b] as [number, number]).sort((x, y) => x[0] - y[0])
  const merge = (rs: [number, number][]) => rs.reduce<[number, number][]>((out, [a, b]) => {
    const last = out[out.length - 1]
    if (last && a <= last[1] + 1) last[1] = Math.max(last[1], b); else out.push([a, b])
    return out
  }, [])
  r = merge(r)
  if (rowsShown(lines, r) > room) throw new Error(`frame.ts: the shown ranges ${JSON.stringify(r)} take ${rowsShown(lines, r)} rows, the editor has ${room}`)
  for (let grew = true; grew;) {
    grew = false
    for (let i = 0; i < r.length; i++) for (const side of [1, 0] as const) {
      const t = r.map(([a, b]) => [a, b] as [number, number])
      if (side === 1 && t[i][1] < lines.length) t[i][1]++
      else if (side === 0 && t[i][0] > 1) t[i][0]--
      else continue
      const m = merge(t)
      if (rowsShown(lines, m) <= room) { r = m; grew = true; break }
    }
  }
  return r
}

export interface Frame {
  /** The side pane's title: the section's mental model, in a few words. */
  model: string
  tree: TreeEntry[]
  /** The file in the editor; `highlight` lines are found by text by the caller (lineOf). `show` is
   *  used only when the highlighted span does not fit the editor. */
  editor: { file: string; code: string; highlight?: number[]; show?: [number, number][]; lang?: Code['lang'] }
  /** The step's session.txt, raw. */
  session: string
  /** The mental model: one diagram, at most one table (check-content holds it to that). */
  side: SceneNode[]
  /** Edges between nodes INSIDE the side pane only. */
  edges?: Edge[]
  project?: string
}

/** The compact explorer (175px) has no room for v1's asides: a note is dropped, the state kept. A
 *  name too long for its level is cut in the middle, its extension kept (the editor's tab has the
 *  whole path): ~19 characters fit at the top level, about one and a half fewer a level down. */
const fit = (name: string, depth: number) => {
  const room = 19 - Math.ceil(depth * 1.5)
  if (name.length <= room) return name
  const dot = name.lastIndexOf('.'), ext = dot > 0 ? name.slice(dot) : ''
  return name.slice(0, room - ext.length - 1) + '…' + ext
}
const bare = (entries: TreeEntry[], depth = 0): TreeEntry[] =>
  entries.map(({ note: _note, children, ...e }) => {
    const named = { ...e, name: fit(e.name, depth) }
    return children ? { ...named, children: bare(children, depth + 1) } : named
  })

export function ideFrame2({ model, tree, editor, session, side, edges = [], project = 'globalbank' }: Frame): SceneModel {
  const term = terminal(session)
  const rows = term.split('\n').length
  if (rows > ROWS - MIN_EDITOR) throw new Error(`frame.ts "${model}": the transcript is ${rows} rows, a terminal shows at most ${ROWS - MIN_EDITOR}`)
  const editorRows = ROWS - Math.max(MIN_TERMINAL, rows)
  const code = trim(editor.code)
  const hl = editor.highlight ?? []
  // A window around the highlight when it fits the editor; `show` (hand-picked ranges) only when not.
  // With no highlight, a hand-picked `show` is the region the section is about (grown to fill).
  let show: [number, number][] | undefined
  try {
    show = hl.length ? windowFor(code, Math.min(...hl), Math.max(...hl), editorRows)
      : editor.show && rowsOf(code.split('\n'), 1, code.split('\n').length) > editorRows ? grow(code, editor.show, editorRows)
      : windowFor(code, 1, 1, editorRows)
  } catch (e) {
    if (!editor.show) throw new Error(`"${model}": ${(e as Error).message}`)
    try { show = grow(code, editor.show, editorRows) } catch (f) { throw new Error(`"${model}": ${(f as Error).message}`) }
  }
  const ed: Code = {
    type: 'code', id: 'editor', filename: editor.file, lang: editor.lang ?? 'python', code, highlight: hl, wrap: true,
    tone: 'ingest', fill: true, w: WORK_W, minH: editorH(editorRows), ...(show && { show }),
  }
  const tm: Code = { type: 'code', id: 'terminal', terminal: true, filename: `terminal — ${project}`, code: term, fill: true, w: WORK_W, minH: FRAME_H - GAP - editorH(editorRows) }
  const explorer: Tree = { type: 'tree', id: 'explorer', title: project, entries: bare(tree), compact: true, fill: true, w: EXPLORER_W, minH: FRAME_H }
  const pane: Group = { type: 'group', id: 'side', title: model, tone: 'ingest', spread: true, w: SIDE_W, minH: FRAME_H, children: side }
  return { dir: 'row', padding: 0.01, nodes: [explorer, { type: 'group', id: 'ide-bench', bare: true, children: [ed, tm] }, pane], edges }
}
