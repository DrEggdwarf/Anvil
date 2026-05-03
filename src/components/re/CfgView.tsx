import { useEffect, useState, useRef } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  BackgroundVariant,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import * as api from '../../api/client'
import { extractBlocks, layoutCfg, blockHeight, BLOCK_W } from './cfgLayout'
import { tokenizeDisasm, tokenColor } from './disasmHighlight'
import type { CfgBlock } from '../../types/re'

// ────────────────────────────────────────────────────────────
// Custom React Flow node — one CFG basic block
// ────────────────────────────────────────────────────────────

interface CfgNodeData extends Record<string, unknown> {
  block: CfgBlock
  isEntry: boolean
  isReturn: boolean
  onClick: (addr: string) => void
}

const FONT_SIZE = 11

function CfgBlockNode({ data }: { data: CfgNodeData }) {
  const { block, isEntry, isReturn, onClick } = data
  const addrHex = `0x${block.offset.toString(16)}`
  const h = blockHeight(block)

  const headerClass = [
    'cfg-node-header',
    isEntry ? 'cfg-node-header--entry' : '',
    isReturn ? 'cfg-node-header--return' : '',
  ].filter(Boolean).join(' ')

  return (
    <div
      className="cfg-node"
      style={{ width: BLOCK_W, height: h }}
      onClick={() => onClick(addrHex)}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />

      <div className={headerClass}>
        {isEntry && <span className="cfg-node-badge cfg-node-badge--entry">ENTRY</span>}
        {isReturn && <span className="cfg-node-badge cfg-node-badge--ret">RET</span>}
        <span className="cfg-node-addr">{addrHex}</span>
        <span className="cfg-node-size">{block.size}b · {block.ops?.length ?? 0} ops</span>
      </div>

      <div className="cfg-node-body">
        {block.ops?.map((op, i) => {
          const tokens = tokenizeDisasm(op.disasm ?? '')
          return (
            <div key={i} className="cfg-node-op" style={{ fontSize: FONT_SIZE }}>
              <span className="cfg-node-op-addr">{`0x${op.offset.toString(16)}`}</span>
              <span className="cfg-node-op-instr">
                {tokens.map((tok, ti) => (
                  <span
                    key={ti}
                    style={{ color: tokenColor(tok.kind, tok.kind === 'mnemonic' ? tok.text : undefined) }}
                  >
                    {tok.text}
                  </span>
                ))}
              </span>
            </div>
          )
        })}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  )
}

const nodeTypes: NodeTypes = { cfgBlock: CfgBlockNode }

// ────────────────────────────────────────────────────────────
// CfgView
// ────────────────────────────────────────────────────────────

interface CfgViewProps {
  sessionId: string | null
  address: string | null
  onNavigate: (address: string) => void
}

export function CfgView({ sessionId, address, onNavigate }: CfgViewProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<CfgNodeData>>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])

  // Stable ref to avoid re-fetching the CFG every time `onNavigate` identity changes.
  const onNavigateRef = useRef(onNavigate)
  useEffect(() => { onNavigateRef.current = onNavigate }, [onNavigate])

  useEffect(() => {
    if (!sessionId || !address) return
    setLoading(true)
    setError(null)

    api.reCfg(sessionId, address)
      .then(raw => {
        const cfgBlocks = extractBlocks(raw)
        const positioned = layoutCfg(cfgBlocks)

        const offsetsWithPred = new Set(
          cfgBlocks.flatMap(b => [b.jump, b.fail].filter((x): x is number => x != null))
        )
        const entryOffset = cfgBlocks.find(b => !offsetsWithPred.has(b.offset))?.offset
          ?? cfgBlocks[0]?.offset

        const rfNodes: Node<CfgNodeData>[] = positioned.map(b => ({
          id: String(b.offset),
          type: 'cfgBlock',
          position: { x: b.x, y: b.y },
          data: {
            block: b,
            isEntry: b.offset === entryOffset,
            isReturn: b.jump == null && b.fail == null,
            onClick: (addr: string) => onNavigateRef.current(addr),
          },
        }))

        const rfEdges: Edge[] = []
        for (const b of cfgBlocks) {
          if (b.jump != null) {
            const isConditional = b.fail != null
            const color = isConditional ? '#22c37a' : '#9b6dff'
            rfEdges.push({
              id: `e-${b.offset}-${b.jump}`,
              source: String(b.offset),
              target: String(b.jump),
              type: 'smoothstep',
              style: { stroke: color, strokeWidth: 1.5 },
              markerEnd: { type: MarkerType.ArrowClosed, color },
              label: isConditional ? 'T' : undefined,
              labelStyle: { fill: color, fontSize: 10, fontWeight: 600 },
              labelBgStyle: { fill: '#1e1e2e' },
            })
          }
          if (b.fail != null) {
            const color = '#f04747'
            rfEdges.push({
              id: `e-${b.offset}-${b.fail}-fail`,
              source: String(b.offset),
              target: String(b.fail),
              type: 'smoothstep',
              style: { stroke: color, strokeWidth: 1.5 },
              markerEnd: { type: MarkerType.ArrowClosed, color },
              label: 'F',
              labelStyle: { fill: color, fontSize: 10, fontWeight: 600 },
              labelBgStyle: { fill: '#1e1e2e' },
            })
          }
        }

        setNodes(rfNodes)
        setEdges(rfEdges)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [sessionId, address, setNodes, setEdges])

  if (!address) return (
    <div className="anvil-re-empty">
      <i className="fa-solid fa-diagram-project" /> Sélectionne une fonction pour afficher son CFG
    </div>
  )
  if (loading) return (
    <div className="anvil-re-loading">
      <i className="fa-solid fa-spinner fa-spin" /> Calcul du CFG…
    </div>
  )
  if (error) return (
    <div className="anvil-re-error">
      <i className="fa-solid fa-triangle-exclamation" /> {error}
    </div>
  )

  return (
    <div className="anvil-cfg-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1, maxZoom: 1.5 }}
        minZoom={0.1}
        maxZoom={3}
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
      >
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const d = node.data as CfgNodeData
            if (d.isEntry) return '#22c37a'
            if (d.isReturn) return '#f04747'
            return '#9b6dff'
          }}
          pannable
          zoomable
        />
        <Background variant={BackgroundVariant.Lines} gap={24} size={1} color="rgba(255,255,255,0.05)" />
      </ReactFlow>

      {/* Legend */}
      <div className="anvil-cfg-legend">
        <span className="anvil-cfg-leg"><span style={{ color: '#22c37a' }}>●</span> True</span>
        <span className="anvil-cfg-leg"><span style={{ color: '#f04747' }}>●</span> False</span>
        <span className="anvil-cfg-leg"><span style={{ color: '#9b6dff' }}>●</span> Goto</span>
      </div>
    </div>
  )
}
