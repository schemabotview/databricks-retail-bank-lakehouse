// The course and scene registries as real objects, for the checks. Both are bundled with esbuild —
// the same modules the app imports, `?raw` spine files included — so a check reads exactly what a
// frame renders, never a regex over source text (a v1 check-content parsed ids out of files and
// could not see a table row, a code line or a scene built by a function).
import { mkdir, readFile, rm } from 'node:fs/promises'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { build } from 'esbuild'

const raw = {
  name: 'raw',
  setup: (b) => {
    b.onResolve({ filter: /\?raw$/ }, (a) => ({ path: join(a.resolveDir, a.path.slice(0, -4)), namespace: 'raw' }))
    b.onLoad({ filter: /.*/, namespace: 'raw' }, async (a) => ({ contents: await readFile(a.path, 'utf8'), loader: 'text' }))
  },
}

// The shell is only needed for SCENE_ASPECT (ide.ts) and slugOf; its stylesheet-free JS bundles into
// node fine. graphl-flow is types-only from scenes, so nothing of it is executed here.
export async function loadRegistry() {
  const temp = join('node_modules', '.cache', 'globalbank-registry')
  await mkdir(temp, { recursive: true })
  const outfile = join(temp, 'registry.mjs')
  await build({
    stdin: { contents: `export { COURSES } from './src/content'\nexport { SCENES } from './src/scenes'\nexport * as IDE from './src/scenes/ide'`, resolveDir: process.cwd(), loader: 'ts' },
    outfile, bundle: true, platform: 'node', format: 'esm', logLevel: 'silent', plugins: [raw],
    external: ['react', 'react-dom', 'react/jsx-runtime', 'lucide-react', '@graphlearning/graphl-flow'],
  })
  try {
    return await import(pathToFileURL(join(process.cwd(), outfile)).href + `?t=${Date.now()}`)
  } finally {
    await rm(temp, { recursive: true, force: true })
  }
}

/** Every node of a scene, depth first, with the id of the top-level pane it sits in. */
export function nodesOf(scene) {
  const out = []
  const walk = (nodes, top) => nodes.forEach((n) => {
    out.push({ node: n, top: top ?? n.id })
    walk(n.children ?? [], top ?? n.id)
  })
  walk(scene.nodes)
  return out
}

/** An IDE frame is one built by src/scenes/ide.ts: it has the template's fixed explorer and side ids. */
export const isIde = (scene) => nodesOf(scene).some(({ node }) => node.id === 'explorer') && nodesOf(scene).some(({ node }) => node.id === 'side')
