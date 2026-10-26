import type { TreeEntry } from '@graphlearning/graphl-flow'

// The explorer from Course 3 on, built from paths: `files` lists what the step's project holds that
// the section is about, in order; a path ending in `/` is a folder drawn collapsed. `mark` sets a
// path's state ('new' this step, 'active' the open file, 'muted'), `note` its aside. Folders that only
// hold listed paths open by themselves. The project grows past what the pane holds, so each section
// lists the files it is about, not every file (check-render fails an explorer that overflows).
export interface Explorer {
  files: string[]
  mark?: Record<string, TreeEntry['state']>
  note?: Record<string, string>
}

export function explorer({ files, mark = {}, note = {} }: Explorer): TreeEntry[] {
  const root: TreeEntry[] = []
  for (const path of files) {
    const folder = path.endsWith('/')
    const parts = path.replace(/\/$/, '').split('/')
    let level = root
    parts.forEach((name, i) => {
      const at = parts.slice(0, i + 1).join('/') + (i < parts.length - 1 || folder ? '/' : '')
      let entry = level.find((e) => e.name === name)
      if (!entry) {
        entry = { name }
        if (mark[at] ?? mark[at.replace(/\/$/, '')]) entry.state = mark[at] ?? mark[at.replace(/\/$/, '')]
        if (note[at] ?? note[at.replace(/\/$/, '')]) entry.note = note[at] ?? note[at.replace(/\/$/, '')]
        level.push(entry)
      }
      if (i < parts.length - 1) level = entry.children ??= []
      else if (folder) entry.folder = true
    })
  }
  return root
}

/** The project's fixed top: the venv and the generated landing files, always collapsed. */
export const BASE = ['.venv/', 'landing/']
export const BASE_NOTE = { '.venv/': 'databricks-connect', 'landing/': 'globalbank_sim' }
export const BASE_MARK = { '.venv/': 'muted' as const }
