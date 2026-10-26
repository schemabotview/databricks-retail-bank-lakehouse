// The content model lives in @graphlearning/shell — the shell renders it, so it owns it. This file
// stays as the repo-local alias every content file imports (`import type { Section } from
// '../types'`), so authoring never names the package.
export type { Section, Course } from '@graphlearning/shell'
