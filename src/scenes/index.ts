import type { SceneModel } from '@graphlearning/graphl-flow'
import { introScenes } from './intro'
import { startScenes } from './start'
import { landScenes } from './land'
import { ledgerScenes } from './ledger'
import { customersScenes } from './customers'
import { protectScenes } from './protect'
import { pipelineScenes } from './pipeline'
import { serveScenes } from './serve'
import { detectScenes } from './detect'
import { scheduleScenes } from './schedule'
import { shipScenes } from './ship'

// Scene registry. Sections reference scenes by id; a graphl-flow scene carries no id of its own, so
// the id is the key here. Scenes are grouped by course (one folder each, mirroring src/content),
// each folder exporting a Record; ids are globally unique, and a duplicate THROWS rather than
// letting one course's scene shadow another's.
const GROUPS: Record<string, SceneModel>[] = [introScenes, startScenes, landScenes, ledgerScenes, customersScenes, protectScenes, pipelineScenes, serveScenes, detectScenes, scheduleScenes, shipScenes]

export const SCENES: Record<string, SceneModel> = {}
for (const group of GROUPS)
  for (const [id, scene] of Object.entries(group)) {
    if (id in SCENES) throw new Error(`scene id "${id}" is registered twice`)
    SCENES[id] = scene
  }

export function getScene(id: string): SceneModel | undefined {
  return SCENES[id]
}
