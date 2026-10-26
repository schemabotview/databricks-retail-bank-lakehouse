import { trim } from './ide'

// A lab's session.txt holds several commands; a concept scene shows each command's real output in
// its own node. `outputOf` cuts one command's output out of the replay, so a full-scene detour
// shows only what scripts/spine.py has verified — never retyped text.
export function outputOf(session: string, command: string): string {
  const blocks = trim(session).split(/^\$ /m).slice(1)
  const block = blocks.find((b) => b.split('\n')[0] === command)
  if (block === undefined) throw new Error(`lab.ts: no command ${JSON.stringify(command)} in the session`)
  return block.split('\n').slice(1).map((line) => line.trimEnd()).join('\n')
}
