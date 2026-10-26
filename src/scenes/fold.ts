import { EDITOR_ROWS, lineOf, lastLine } from './ide'

/**
 * Fold a file longer than the editor to the region a section is about: lines 1–`head` (the file's
 * header; 0 folds everything above), then from the line containing `first` through the line containing `last` (or as far as
 * the editor allows). Found by TEXT, like every highlight. Each skipped run is one fold row, and
 * the result never exceeds EDITOR_ROWS — check-content would fail it.
 */
export function view(code: string, first: string, last?: string, head = 2): { show: [number, number][] } {
  const n = lastLine(code)
  if (n <= EDITOR_ROWS) return { show: [[1, n]] }
  const a = lineOf(code, first)
  const keepHead = head > 0 && a > head + 1 // lines 1–head, a fold, then the region
  const start = keepHead || head === 0 ? a : 1 // head 0: fold everything above the region
  const used = keepHead ? head + 1 : start > 1 ? 1 : 0
  const room = EDITOR_ROWS - used - 1 // the trailing fold row, if any
  const want = last ? lineOf(code, last, a) : n
  const b = Math.min(want, start + room - 1, n)
  return { show: [...(keepHead ? [[1, head] as [number, number]] : []), [start, b === n - 1 ? n : b]] }
}
