// Capture sections the way the recorder frames them — a 3840×2160 viewport at deviceScaleFactor 1,
// `?capture=1#/<slug>`, after graphl-flow's data-fit="ready" — with every SVG paused at t = 0 so a
// still is reproducible. This is the "look at it" step every check is a floor under.
//
//   npm run shots                       every section
//   npm run shots -- start-a-venv ...   only these slugs (or slug prefixes: `start` for a course)
//
// PNGs land in out/shots/<slug>.png (out/ is gitignored). Boots its own vite on :5192.
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'
import { createServer } from 'vite'
import { loadRegistry } from './registry.mjs'

const { COURSES } = await loadRegistry()
const asked = process.argv.slice(2)
const slugs = Object.values(COURSES).flatMap((c) => c.sections.map((s) => `${c.id}-${s.id}`)).filter((s) => !asked.length || asked.some((a) => s.startsWith(a)))
if (!slugs.length) {
  console.error(`✗ no section matches ${asked.join(' ')}`)
  process.exit(1)
}
const out = 'out/shots'
await mkdir(out, { recursive: true })
const server = await createServer({ server: { host: '127.0.0.1', port: 5192, strictPort: true }, logLevel: 'silent' })
await server.listen()
const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width: 3840, height: 2160 }, deviceScaleFactor: 1 })
  for (const slug of slugs) {
    await page.goto('about:blank') // a fresh Scene per section — see check-render.mjs
    await page.goto(`http://127.0.0.1:5192/?capture=1#/${slug}`)
    await page.waitForSelector('.gf-scene[data-fit="ready"]', { timeout: 20000 })
    await page.evaluate(() => document.querySelectorAll('svg').forEach((s) => { s.pauseAnimations?.(); s.setCurrentTime?.(0) }))
    await page.screenshot({ path: `${out}/${slug}.png` })
    console.log(`${out}/${slug}.png`)
  }
} finally {
  await browser.close()
  await server.close()
}
