import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Three stylesheets, in cascade order — the last one wins, and it is the only one this repo owns:
//   engine — @graphlearning/graphl-flow's node styles and the IBM Plex faces (Mono: code and tables)
//   shell  — the concept-app layout and surface (it paints --bg, the canvas the engine's theme matches)
//   theme  — this repo's brand token
// The order is load-bearing: theme last, or this repo's brand loses to the shell's neutral default.
import '@graphlearning/graphl-flow/styles.css'
import '@graphlearning/shell/styles.css'
import './theme.css'
import { ConceptApp } from '@graphlearning/shell'
import { COURSES } from './content'
import { getScene } from './scenes'

// The whole app. Router, section view, catalog and narration are all @graphlearning/shell; this repo
// supplies its two registries and its name.
//
// audioBase must be passed from here: import.meta.env.BASE_URL is replaced at THIS app's build time
// (vite `base` = "/<repo-slug>/"), and the shell is built separately, so it cannot read it.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConceptApp subject="Databricks" courses={COURSES} getScene={getScene} audioBase={import.meta.env.BASE_URL} />
  </StrictMode>,
)
