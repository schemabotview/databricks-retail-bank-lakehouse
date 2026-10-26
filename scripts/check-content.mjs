// Content guard — silent failures that build green and break only on screen or in the recording.
// It reads the REAL registries (scripts/registry.mjs bundles src/content and src/scenes), so it sees
// exactly what renders:
//
//   1. A section must be scene-only and narrated, and its scene must exist.
//   2. Node ids are unique within a scene (graphl-flow resolves edges and focus by id).
//   3. An IDE side pane is a DIAGRAM (COURSE-PLAN.md, "The side pane is a diagram"): it holds
//      an edge, a plot or a table (python-ct's v1 panes were 79 bullet lists and one edge in 90
//      sections). A bulleted card in a side pane is a caption, so it holds ≤ 3 bullets.
//   4. An IDE frame draws edges only INSIDE its side pane: an edge between panes widens the gap it
//      crosses (graphl-flow's EDGE_GAP) and moves every pane off the shared template.
//   5. An IDE frame's editor shows no more rows than EDITOR_ROWS (fold with `show`), its lines fit
//      EDITOR_COLS, and its terminal no more lines than TERMINAL_ROWS: a pane's floor lets content
//      grow it, which moves the whole template — check-render would only see "the fit differs".
//   6. Once a course has narration audio, every section of it has its wav — a missing or renamed one
//      plays silence and records a silent segment, with no error anywhere.
//
// What renders is checked by scripts/check-render.mjs: focus landing, overflow, edges, fit, panes.
//
// Run: npm run check
import { existsSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { isIde, loadRegistry, nodesOf } from './registry.mjs'

const { COURSES, SCENES, IDE } = await loadRegistry()
const problems = []
const MAX_CAPTION_BULLETS = 3

// --- 1. sections --------------------------------------------------------------------------------
for (const course of Object.values(COURSES))
  for (const section of course.sections) {
    const at = `${course.id}-${section.id}`
    if ('slide' in section) problems.push(`${at}  has a slide — sections in this repo are scene-only`)
    if (!section.narration?.trim()) problems.push(`${at}  has no narration`)
    if (!SCENES[section.scene]) problems.push(`${at}  scene '${section.scene}' is not registered`)
  }

for (const [id, scene] of Object.entries(SCENES)) {
  const all = nodesOf(scene)
  // --- 2. unique ids ----------------------------------------------------------------------------
  const seen = new Set()
  for (const { node } of all) {
    if (seen.has(node.id)) problems.push(`scene ${id}  node id '${node.id}' is used twice`)
    seen.add(node.id)
  }
  if (!isIde(scene)) continue
  const top = new Map(all.map(({ node, top }) => [node.id, top]))
  const side = all.filter(({ top }) => top === 'side').map(({ node }) => node)
  // An endpoint is a node id or `<table>.<row>` / `<code>.L<n>` / `<tree>.<path>`: its node is the
  // part before the first dot.
  const paneOf = (end) => top.get(end.split('.')[0])
  // --- 4. edges stay inside the side pane --------------------------------------------------------
  const edges = scene.edges ?? []
  for (const e of edges)
    for (const end of [e.from, e.to])
      if (paneOf(end) !== 'side') problems.push(`scene ${id}  edge ${e.from} → ${e.to}: '${end}' is ${paneOf(end) ? `in the ${paneOf(end)} pane` : 'not a node'} — IDE edges stay inside the side pane`)
  // --- 3. the side pane is a diagram ---------------------------------------------------------------
  const sideEdges = edges.filter((e) => paneOf(e.from) === 'side' && paneOf(e.to) === 'side')
  if (!sideEdges.length && !side.some((n) => n.type === 'table' || n.type === 'plot'))
    problems.push(`scene ${id}  the side pane holds no edge, plot or table — it must carry a diagram, not a list`)
  // --- 5. the editor and terminal hold what they show -------------------------------------------
  // Rows as graphl-flow draws them (Code.tsx codeRows): every line, or the `show` ranges with each
  // skipped run folded to one row. graphl-flow drops a template literal's common indent; spine files
  // have none.
  const editor = all.find(({ node }) => node.id === 'editor')?.node
  const term = all.find(({ node }) => node.id === 'terminal')?.node
  if (editor) {
    const lines = editor.code.split('\n')
    const keep = editor.show && new Set(editor.show.flatMap(([a, b]) => Array.from({ length: b - a + 1 }, (_, i) => a + i)))
    // A kept line is a row; each RUN of skipped lines is one fold row.
    const rows = keep ? lines.filter((_, i) => keep.has(i + 1) || i === 0 || keep.has(i)).length : lines.length
    if (rows > IDE.EDITOR_ROWS) problems.push(`scene ${id}  the editor shows ${rows} rows; it holds ${IDE.EDITOR_ROWS} — fold with show`)
    const shown = lines.filter((_, i) => !keep || keep.has(i + 1))
    const wide = shown.find((l) => l.length > IDE.EDITOR_COLS)
    if (wide) problems.push(`scene ${id}  a line is ${wide.length} columns; the editor holds ${IDE.EDITOR_COLS} — "${wide.slice(0, 40)}…"`)
  }
  if (term) {
    const lines = term.code.split('\n')
    if (lines.length > IDE.TERMINAL_ROWS) problems.push(`scene ${id}  the terminal shows ${lines.length} lines; it holds ${IDE.TERMINAL_ROWS} — shorten the session`)
    const wide = lines.find((l) => l.replace(/^! /, '').length > IDE.EDITOR_COLS)
    if (wide) problems.push(`scene ${id}  a terminal line is longer than ${IDE.EDITOR_COLS} columns — "${wide.slice(0, 40)}…"`)
  }
  for (const n of side)
    if (n.type === 'item' && (n.bullets?.length ?? 0) > MAX_CAPTION_BULLETS)
      problems.push(`scene ${id}  '${n.id}' has ${n.bullets.length} bullets — a side-pane list is a caption (≤ ${MAX_CAPTION_BULLETS}); draw the rest`)
}

// --- 6. every section has its narration wav, once its course has any -----------------------------
// public/audio/<course>/<section-id>.wav. Gated PER COURSE on that course having at least one wav:
// audio is one Colab pass after a course's frames are approved, and reporting a whole course of
// known-missing files on every run trains you to ignore the guard.
const audio = 'public/audio'
for (const course of Object.values(COURSES)) {
  const dir = join(audio, course.id)
  if (!existsSync(dir) || !statSync(dir).isDirectory() || !readdirSync(dir).some((f) => f.endsWith('.wav'))) continue
  for (const section of course.sections) {
    const wav = join(dir, `${section.id}.wav`)
    if (!existsSync(wav)) problems.push(`${course.id}-${section.id}  no narration wav at ${wav} — the section plays silence`)
  }
}

if (problems.length) {
  console.error(`✗ ${problems.length} content problem(s):\n` + problems.map((p) => '  ' + p).join('\n'))
  process.exit(1)
}
const sections = Object.values(COURSES).reduce((n, c) => n + c.sections.length, 0)
console.log(`✓ content OK — ${sections} section(s), ${Object.keys(SCENES).length} scene(s), every IDE side pane a diagram`)
