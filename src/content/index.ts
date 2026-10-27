import { intro } from './intro'
import { start } from './start'
import { land } from './land'
import { customers } from './customers'
import type { Course, Section } from './types'

// Course registry, in syllabus order. One course per course of COURSE-PLAN.md; a course is
// registered here only once it is authored.
export const COURSES: Record<string, Course> = {
  [intro.id]: intro,
  [start.id]: start,
  [land.id]: land,
  [customers.id]: customers,
}

export type { Course, Section }

// slugOf / allSections are the shell's — the slug rule (`<courseId>-<sectionId>`) is part of the
// route contract every recorder drives, so it cannot be a per-repo decision. Re-exported here
// because this module is what the app and the scripts import them from.
export { slugOf, allSections } from '@graphlearning/shell'

export function getCourse(id: string): Course | undefined {
  return COURSES[id]
}
