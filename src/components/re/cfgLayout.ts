import dagre from '@dagrejs/dagre'
import type { CfgBlock, CfgGraph } from '../../types/re'

export const BLOCK_W = 290
export const BLOCK_HEADER_H = 26
export const LINE_H = 16
export const BLOCK_PAD_Y = 10

export interface PositionedBlock extends CfgBlock {
  x: number
  y: number
  w: number
  h: number
}

/** Extract blocks from agj output (handles [{name, blocks:[...]}] or flat [{...}] format). */
export function extractBlocks(raw: CfgGraph[] | CfgBlock[]): CfgBlock[] {
  if (!raw.length) return []
  const first = raw[0] as unknown as Record<string, unknown>
  if ('blocks' in first && Array.isArray(first.blocks)) {
    return (first as unknown as CfgGraph).blocks
  }
  return raw as CfgBlock[]
}

export function blockHeight(b: CfgBlock): number {
  return BLOCK_HEADER_H + (b.ops?.length ?? 1) * LINE_H + BLOCK_PAD_Y
}

/**
 * Lay out CFG blocks using dagre (proper hierarchical DAG layout).
 * Returns PositionedBlock[] with x/y as top-left corner of each block.
 *
 * Post-processing aligns the True/False targets of every conditional branch
 * onto the same rank (Y) — like Power Automate / n8n / Cutter. Back-edges
 * (loops) are skipped from this alignment so they don't drag descendants up.
 */
export function layoutCfg(blocks: CfgBlock[]): PositionedBlock[] {
  if (!blocks.length) return []

  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 90, ranksep: 70, marginx: 30, marginy: 30 })
  g.setDefaultEdgeLabel(() => ({}))

  for (const b of blocks) {
    const h = blockHeight(b)
    g.setNode(String(b.offset), { width: BLOCK_W, height: h })
  }
  for (const b of blocks) {
    if (b.jump != null) g.setEdge(String(b.offset), String(b.jump))
    if (b.fail != null) g.setEdge(String(b.offset), String(b.fail))
  }

  dagre.layout(g)

  // Snapshot dagre Y per node (centre).
  const yMap = new Map<number, number>()
  const heightByOffset = new Map<number, number>()
  for (const b of blocks) {
    yMap.set(b.offset, g.node(String(b.offset)).y)
    heightByOffset.set(b.offset, blockHeight(b))
  }

  // Detect back-edges to skip them in the alignment pass.
  const isBackEdge = (src: number, dst: number) => {
    const ys = yMap.get(src), yd = yMap.get(dst)
    return ys != null && yd != null && yd <= ys
  }

  // Build forward-only adjacency (skip back-edges).
  const children = new Map<number, number[]>()
  for (const b of blocks) {
    const kids: number[] = []
    if (b.jump != null && !isBackEdge(b.offset, b.jump)) kids.push(b.jump)
    if (b.fail != null && !isBackEdge(b.offset, b.fail)) kids.push(b.fail)
    children.set(b.offset, kids)
  }

  // Forward parents (used to detect join nodes / shared descendants).
  const parents = new Map<number, number[]>()
  for (const [src, kids] of children) {
    for (const k of kids) {
      const arr = parents.get(k) ?? []
      arr.push(src)
      parents.set(k, arr)
    }
  }

  // Collect the forward subtree of a root (set of node offsets).
  const subtreeOf = (root: number) => {
    const visited = new Set<number>()
    const stack = [root]
    while (stack.length) {
      const n = stack.pop()!
      if (visited.has(n)) continue
      visited.add(n)
      for (const c of children.get(n) ?? []) if (!visited.has(c)) stack.push(c)
    }
    return visited
  }

  // Shift only nodes whose ALL forward parents are inside `owned` — i.e.
  // exclusive descendants. Join nodes (with parents outside the subtree)
  // stay put so they don't ride along and overlap the other branch.
  const shiftExclusive = (owned: Set<number>, dy: number) => {
    if (dy === 0) return
    for (const n of owned) {
      const ps = parents.get(n) ?? []
      // Root of the shifted subtree always moves; otherwise require all
      // parents to be inside `owned`.
      const allParentsInside = ps.length === 0 || ps.every(p => owned.has(p))
      if (allParentsInside || ps.length === 0) {
        yMap.set(n, (yMap.get(n) ?? 0) + dy)
      }
    }
  }

  // Two passes for nested conditionals. Align T/F siblings by the smallest
  // top (= closest to parent) without dragging shared descendants along.
  for (let pass = 0; pass < 2; pass++) {
    for (const b of blocks) {
      if (b.jump == null || b.fail == null) continue
      if (isBackEdge(b.offset, b.jump) || isBackEdge(b.offset, b.fail)) continue
      const hj = heightByOffset.get(b.jump) ?? 0
      const hf = heightByOffset.get(b.fail) ?? 0
      const topJ = (yMap.get(b.jump)!) - hj / 2
      const topF = (yMap.get(b.fail)!) - hf / 2
      const targetTop = Math.min(topJ, topF)
      shiftExclusive(subtreeOf(b.jump), targetTop - topJ)
      shiftExclusive(subtreeOf(b.fail), targetTop - topF)
    }
  }

  return blocks.map(b => {
    const cy = yMap.get(b.offset)!
    const node = g.node(String(b.offset))
    const h = blockHeight(b)
    return {
      ...b,
      x: node.x - BLOCK_W / 2,
      y: cy - h / 2,
      w: BLOCK_W,
      h,
    }
  })
}
