#!/usr/bin/env node
// The YouTube thumbnail for the single full-course film (scripts/out/film.mp4).
//
// Not the shell's `graphl-thumb`: that template is a PER-COURSE poster (58% scene + panel), and a
// cropped 16:9 video frame turns to mush at the ~168px the mobile feed actually renders. A film
// cover needs poster grammar — few elements, enormous type, one focal object.
//
// The terminal card is REAL: every row is cut out of a spine session.txt, the same replayed output
// the scenes use, so the thumbnail cannot promise a lakehouse the course does not build.

import { mkdirSync, readFileSync, writeFileSync, existsSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, dirname, isAbsolute } from 'node:path'
import { createRequire } from 'node:module'

const repoDir = process.cwd()
const dataDir = join(repoDir, 'scripts')
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

const SCALE = 2
const W = 1280 * SCALE
const H = 720 * SCALE

const requireFromRepo = createRequire(join(repoDir, 'package.json'))
async function loadPeer(name) {
  const { pathToFileURL } = await import('node:url')
  return import(pathToFileURL(requireFromRepo.resolve(name)).href)
}

// ── the real output ─────────────────────────────────────────────────────────────────────────────
// §7.9's session: `globalbank.counts` prints the medallion with the row counts the workspace
// actually returned. Four lines carry the whole film — bronze, silver, gold, by name and by size.
const SESSION = join(repoDir, 'spine', 'pipeline', '09-full-refresh', 'session.txt')

function realCounts() {
  const lines = readFileSync(SESSION, 'utf8').split('\n').map((l) => l.trimEnd())
  const i = lines.findIndex((l) => /^\$ .*globalbank\.counts\s*$/.test(l))
  if (i < 0) throw new Error(`no 'globalbank.counts' command in ${SESSION}`)
  const cmd = lines[i].replace(/^\$ /, '')
  const rows = []
  for (let j = i + 1; j < lines.length && !lines[j].startsWith('$'); j++) {
    const m = lines[j].match(/^\s+(\w+)\.(\S+)\s+([\d,]+)\s+rows\s*$/)
    if (!m) continue
    rows.push({ layer: m[1], table: m[2], rows: m[3] })
  }
  if (rows.length < 3) throw new Error(`expected the medallion counts in ${SESSION}, got ${rows.length} row(s)`)
  for (const want of ['bronze', 'silver', 'gold']) {
    if (!rows.some((r) => r.layer === want)) throw new Error(`no ${want} row in the real counts`)
  }
  return { cmd, rows }
}

// ── the page ────────────────────────────────────────────────────────────────────────────────────
const fontFace = (fam, weight, file) => {
  const b64 = readFileSync(join(repoDir, 'node_modules', '@fontsource', fam, 'files', file)).toString('base64')
  return `@font-face{font-family:'${fam === 'ibm-plex-mono' ? 'IBM Plex Mono' : 'IBM Plex Sans'}';`
    + `font-weight:${weight};font-style:normal;font-display:block;`
    + `src:url(data:font/woff2;base64,${b64}) format('woff2')}`
}

// The scene engine's tone palette (@graphlearning/graphl-flow), its dark row — the card is dark in
// every theme. Using these instead of invented colours paints the cover like the scenes.
const TONE = {
  ingest: '#4f8ff7',   // bronze: what arrives
  store:  '#37b877',   // silver: what is correct
  serve:  '#f0902f',   // gold: what is ready
  muted:  'rgba(255,255,255,.55)',
}
const LAYER_COLOUR = { bronze: TONE.ingest, silver: TONE.store, gold: TONE.serve }

const BRAND = '#ff3621' // --brand, as in theme.css and the favicon tile

const THEMES = {
  dark: {
    bg: '#0b0f14', card: '#141b24', ink: '#ffffff', accent: BRAND, badgeInk: '#ffffff',
    rule: 'rgba(255,255,255,.14)',
    glow: 'radial-gradient(118% 104% at 8% 10%, #2a1510 0%, #0b0f14 58%)',
  },
  ember: {
    bg: '#14100e', card: '#1d1714', ink: '#ffffff', accent: BRAND, badgeInk: '#ffffff',
    rule: 'rgba(255,255,255,.13)',
    glow: 'radial-gradient(118% 104% at 70% 34%, #5c2418 0%, #14100e 60%)',
  },
  light: {
    bg: '#f4f6fa', card: '#141b24', ink: '#0d1220', accent: BRAND, badgeInk: '#ffffff',
    rule: 'rgba(0,0,0,.12)',
    glow: 'radial-gradient(120% 120% at 10% 8%, #ffffff 0%, #e9edf3 70%)',
  },
}

/**
 * Our own mark, not the Databricks one. The Databricks name and logo are its trademarks; this is an
 * independent course, a monetised channel is a commercial use, and nothing here is endorsed by
 * them. So the cover carries the layers glyph — lucide's geometry (ISC), the mark CLAUDE.md already
 * uses for Delta throughout the scenes, and literally what the card beside it shows.
 */
function markSvg(colour) {
  const file = join(repoDir, 'node_modules', 'lucide-react', 'dist', 'esm', 'icons', 'layers.mjs')
  const nodes = [...readFileSync(file, 'utf8').matchAll(/\[\s*"(\w+)",\s*\{([^}]*)\}\s*\]/g)]
    .map((m) => {
      const attrs = [...m[2].matchAll(/(\w+):\s*"([^"]*)"/g)]
        .filter(([, k]) => k !== 'key').map(([, k, v]) => `${k}="${v}"`).join(' ')
      return `<${m[1]} ${attrs}/>`
    }).join('')
  if (!nodes) throw new Error('no geometry in lucide icon "layers"')
  return `<svg class="logo" viewBox="0 0 24 24" fill="none" stroke="${colour}" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Lakehouse layers — GraphL"
    xmlns="http://www.w3.org/2000/svg">${nodes}</svg>`
}

/**
 * The medallion, built from the SAME parsed session rows as the terminal card — the layer bands
 * carry the counts the workspace returned, so the diagram promises nothing the course does not
 * build. Drawn rather than listed because a shape survives the ~336px the mobile feed renders,
 * where a column of monospace text does not.
 */
function medallionHtml(counts) {
  const BANDS = [
    { layer: 'bronze', what: 'as it arrived' },
    { layer: 'silver', what: 'correct, joined' },
    { layer: 'gold', what: 'ready to read' },
  ]
  return BANDS.map(({ layer, what }, i) => {
    // One band per layer; where a layer has several tables the counts sum, and the band says so.
    const mine = counts.rows.filter((r) => r.layer === layer)
    if (!mine.length) throw new Error(`no ${layer} row to draw`)
    const total = mine.reduce((a, r) => a + Number(r.rows.replace(/,/g, '')), 0)
    const col = LAYER_COLOUR[layer]
    const label = mine.length > 1 ? `${mine.length} tables` : mine[0].table
    return (i ? `<div class="arrow"><svg viewBox="0 0 24 24" fill="none" stroke="${col}"
        stroke-width="3" stroke-linecap="round" stroke-linejoin="round"
        xmlns="http://www.w3.org/2000/svg"><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg></div>` : '')
      + `<div class="band" style="background:${col}1f;border-color:${col}">
           <span class="bname" style="color:${col}">${esc(layer)}</span>
           <span class="bwhat">${esc(what)}</span>
           <span class="bn">${total.toLocaleString('en-US')}</span>
           <span class="bunit">rows</span>
           <span class="btbl">${esc(label)}</span>
         </div>`
  }).join('')
}

function pageHtml({ counts, theme, head1, head2, badge, card }) {
  const t = THEMES[theme]
  const fonts = [
    fontFace('ibm-plex-sans', 700, 'ibm-plex-sans-latin-700-normal.woff2'),
    fontFace('ibm-plex-sans', 600, 'ibm-plex-sans-latin-600-normal.woff2'),
    fontFace('ibm-plex-mono', 600, 'ibm-plex-mono-latin-600-normal.woff2'),
    fontFace('ibm-plex-mono', 400, 'ibm-plex-mono-latin-400-normal.woff2'),
  ].join('')

  // One grid for the whole table, so every column lines up across rows and nothing can collide.
  const cells = counts.rows.map((r) => {
    const col = LAYER_COLOUR[r.layer] ?? TONE.muted
    return `<span class="layer" style="color:${col}">${esc(r.layer)}</span>`
      + `<span class="tbl">${esc(r.table)}</span>`
      + `<span class="n">${esc(r.rows)}</span>`
      + `<span class="unit">rows</span>`
  }).join('')

  return `<style>
  ${fonts}
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{width:${W}px;height:${H}px;overflow:hidden}
  body{background:${t.bg};background-image:${t.glow};
       font-family:'IBM Plex Sans',system-ui,sans-serif;color:${t.ink};
       display:flex;align-items:stretch;gap:${38 * SCALE}px;padding:${46 * SCALE}px ${50 * SCALE}px}

  .left{flex:0 0 ${490 * SCALE}px;display:flex;flex-direction:column;justify-content:center}
  .logo{width:${92 * SCALE}px;height:${92 * SCALE}px;display:block;
        margin-bottom:${20 * SCALE}px;align-self:flex-start}
  .h{font-weight:700;line-height:.86;letter-spacing:-.045em;white-space:nowrap}
  .h1{font-size:${94 * SCALE}px}
  .h2{font-size:${94 * SCALE}px;color:${t.accent};letter-spacing:-.05em}
  .badge{align-self:flex-start;margin-top:${28 * SCALE}px;padding:${11 * SCALE}px ${22 * SCALE}px;
         background:${t.accent};border-radius:${12 * SCALE}px;
         font-weight:700;font-size:${30 * SCALE}px;letter-spacing:.055em;color:${t.badgeInk}}

  .card{flex:1;min-width:0;background:${t.card};border:${1 * SCALE}px solid ${t.rule};
        border-radius:${18 * SCALE}px;padding:${26 * SCALE}px ${30 * SCALE}px ${24 * SCALE}px;
        display:flex;flex-direction:column;box-shadow:0 ${22 * SCALE}px ${64 * SCALE}px rgba(0,0,0,.5)}
  .dots{display:flex;gap:${9 * SCALE}px;margin-bottom:${16 * SCALE}px}
  .dots i{width:${13 * SCALE}px;height:${13 * SCALE}px;border-radius:50%}
  .cmd{font-family:'IBM Plex Mono',monospace;font-size:${25 * SCALE}px;font-weight:400;
       color:rgba(255,255,255,.62);margin-bottom:${20 * SCALE}px;white-space:nowrap}
  .cmd b{color:#6ee787;font-weight:400}

  .rows{flex:1;display:grid;align-content:center;
        grid-template-columns:auto 1fr auto auto;
        column-gap:${14 * SCALE}px;row-gap:${38 * SCALE}px;
        font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:${27 * SCALE}px;color:#fff}
  .layer{letter-spacing:-.02em;font-weight:600}
  .tbl{color:rgba(255,255,255,.72);font-weight:400;letter-spacing:-.02em;white-space:nowrap}
  .n{text-align:right;color:#fff;font-weight:600}
  .unit{color:rgba(255,255,255,.42);font-weight:400;font-size:${22 * SCALE}px}
  .medallion{flex:1;display:flex;flex-direction:column;justify-content:center;
             gap:${4 * SCALE}px}
  .band{display:grid;grid-template-columns:auto 1fr auto auto;align-items:baseline;
        column-gap:${12 * SCALE}px;row-gap:0;
        border:${2 * SCALE}px solid;border-radius:${14 * SCALE}px;
        padding:${15 * SCALE}px ${20 * SCALE}px ${13 * SCALE}px}
  .bname{font-family:'IBM Plex Sans',system-ui,sans-serif;font-weight:700;
         font-size:${44 * SCALE}px;letter-spacing:-.03em;line-height:1}
  .bwhat{font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:${23 * SCALE}px;
         color:rgba(255,255,255,.5);white-space:nowrap}
  .bn{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:${40 * SCALE}px;
      color:#fff;letter-spacing:-.02em;text-align:right}
  .bunit{font-family:'IBM Plex Mono',monospace;font-size:${22 * SCALE}px;
         color:rgba(255,255,255,.42)}
  .btbl{grid-column:1 / -1;font-family:'IBM Plex Mono',monospace;font-size:${22 * SCALE}px;
        color:rgba(255,255,255,.44);margin-top:${5 * SCALE}px;white-space:nowrap}
  .arrow{display:flex;justify-content:center;margin:${-1 * SCALE}px 0}
  .arrow svg{width:${30 * SCALE}px;height:${30 * SCALE}px}

  .foot{margin-top:${18 * SCALE}px;white-space:nowrap;font-family:'IBM Plex Mono',monospace;
        font-size:${23 * SCALE}px;color:rgba(255,255,255,.4);letter-spacing:.03em}
</style>
<div class="left">
  ${markSvg(theme === 'light' ? t.accent : '#ffffff')}
  <div class="h h1">${esc(head1)}</div>
  <div class="h h2">${esc(head2)}</div>
  <div class="badge">${esc(badge)}</div>
</div>
<div class="card">
  ${card === 'medallion'
    ? `<div class="medallion">${medallionHtml(counts)}</div>
       <div class="foot">real output · globalbank.counts</div>`
    : `<div class="dots"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>
       <div class="cmd">$ <b>${esc(counts.cmd)}</b></div>
       <div class="rows">${cells}</div>
       <div class="foot">landing → bronze → silver → gold</div>`}
</div>`
}

// ── render ──────────────────────────────────────────────────────────────────────────────────────
function parse(argv) {
  const o = { theme: 'dark', out: null, head1: 'LEARN', head2: 'DATABRICKS',
              badge: 'FULL COURSE', all: false, card: 'medallion' }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--theme') o.theme = argv[++i]
    else if (a === '--card') o.card = argv[++i]
    else if (a === '--out') o.out = argv[++i]
    else if (a === '--head1') o.head1 = argv[++i]
    else if (a === '--head2') o.head2 = argv[++i]
    else if (a === '--badge') o.badge = argv[++i]
    else if (a === '--all') o.all = true
    else { console.error(`unknown argument: ${a}`); process.exit(2) }
  }
  return o
}

async function shoot(page, opt, counts, outFile) {
  if (!THEMES[opt.theme]) throw new Error(`unknown theme "${opt.theme}" (have: ${Object.keys(THEMES).join(', ')})`)
  if (!['terminal', 'medallion'].includes(opt.card)) throw new Error(`unknown --card "${opt.card}"`)
  const html = pageHtml({ counts, theme: opt.theme, head1: opt.head1, head2: opt.head2,
                          badge: opt.badge, card: opt.card })
  await page.setContent(html, { waitUntil: 'load' })
  await page.evaluate(async () => { if (document.fonts?.ready) await document.fonts.ready })
  mkdirSync(dirname(outFile), { recursive: true })
  await page.screenshot({ path: outFile, type: 'png' })
  console.log(`✅ ${outFile}   ${W}×${H}  (${opt.theme}, ${opt.card})`)
}

const opt = parse(process.argv.slice(2))
const counts = realCounts()
console.log(`Real output from spine/pipeline/09-full-refresh: ${counts.rows.length} rows`)

const puppeteer = (await loadPeer('puppeteer')).default
const userDataDir = join(tmpdir(), `thumb-film-${process.pid}`)
const browser = await puppeteer.launch({
  headless: true, userDataDir,
  defaultViewport: { width: W, height: H, deviceScaleFactor: 1 },
})
try {
  const page = await browser.newPage()
  const outDir = join(repoDir, 'output', 'thumbnails')
  if (opt.all) {
    for (const theme of Object.keys(THEMES)) {
      await shoot(page, { ...opt, theme }, counts, join(outDir, `film-${theme}.png`))
    }
    for (const card of ['terminal', 'medallion']) {
      await shoot(page, { ...opt, theme: 'dark', card }, counts, join(outDir, `film-${card}.png`))
    }
    await shoot(page, { ...opt, theme: 'dark' }, counts, join(outDir, 'film.png'))
  } else {
    const file = opt.out
      ? (isAbsolute(opt.out) ? opt.out : join(repoDir, opt.out))
      : join(outDir, 'film.png')
    await shoot(page, opt, counts, file)
  }
} finally {
  await browser.close()
  rmSync(userDataDir, { recursive: true, force: true })
}
