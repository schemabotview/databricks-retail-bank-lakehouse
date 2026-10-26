import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The render engine and the app shell are the @graphlearning/graphl-flow and @graphlearning/shell packages,
// not local folders. `dedupe` is what keeps a single copy of react / react-dom
// across this app and both packages — the gotcha that bites when two React copies meet
// (invalid-hook-call). The packages declare them as peer deps and externalise them, so neither ever
// carries its own React; dedupe is the belt to that braces. jsx is automatic with
// @vitejs/plugin-react.
//
// `base` is `/<repo-slug>/` for the production BUILD only. The app deploys under
// graphl.in/<repo-slug>/ as a concept app in the GraphL catalog — matching the repo name
// schemabotview/<repo-slug> — so built asset URLs must be subpath-relative. Dev/serve stays at `/`
// so `npm run dev` and the capture/record scripts (which drive the dev server at
// localhost:5173/#/<slug>) are unaffected.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/databricks-retail-bank-lakehouse/' : '/',
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
  },
  server: { port: 5173 },
}))
