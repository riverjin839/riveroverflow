import { useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import * as THREE from 'three'
import type { OntologyObject, OntologyLink } from '../../models/ontologyStore'

type Props = {
  objects: OntologyObject[]
  links: OntologyLink[]
}

// Claude 다크 팔레트 + 객체 타입별 강조색
const TYPE_COLOR: Record<string, string> = {
  stock: '#f97316',      // brand orange
  strategy: '#fbbf24',   // amber
  trade: '#34d399',      // emerald
  research: '#a78bfa',   // violet
  signal: '#f472b6',     // pink
}

const BG_COLOR = '#0b1220'
const LINK_COLOR = 'rgba(148, 163, 184, 0.35)'  // slate-400
const LABEL_COLOR = '#f1f5f9'

type GraphNode = {
  id: string
  name: string
  type: string
  color: string
  val: number
}

type GraphLink = {
  source: string
  target: string
  predicate: string
}

export default function Ontology3DView({ objects, links }: Props) {
  const graphRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ width: 800, height: 560 })
  const [activeType, setActiveType] = useState<string | 'all'>('all')
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current
    const resize = () => {
      setDims({ width: el.clientWidth, height: el.clientHeight })
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const data = useMemo(() => {
    const typeCount: Record<string, number> = {}
    objects.forEach((o) => {
      typeCount[o.type] = (typeCount[o.type] ?? 0) + 1
    })
    const nodes: GraphNode[] = objects
      .filter((o) => activeType === 'all' || o.type === activeType)
      .map((o) => ({
        id: o.key,
        name: (o.properties?.name as string) || o.key,
        type: o.type,
        color: TYPE_COLOR[o.type] ?? '#94a3b8',
        val: 2 + Math.log((typeCount[o.type] ?? 1) + 1),
      }))
    const visibleKeys = new Set(nodes.map((n) => n.id))
    const edges: GraphLink[] = links
      .filter((l) => visibleKeys.has(l.subject_key) && visibleKeys.has(l.object_key))
      .map((l) => ({
        source: l.subject_key,
        target: l.object_key,
        predicate: l.predicate,
      }))
    return { nodes, links: edges }
  }, [objects, links, activeType])

  const types = useMemo(() => Array.from(new Set(objects.map((o) => o.type))).sort(), [objects])

  function focusOnNode(node: GraphNode) {
    const graph = graphRef.current
    if (!graph) return
    const distance = 140
    const n: any = node
    if (n.x == null) return
    const distRatio = 1 + distance / Math.hypot(n.x, n.y, n.z)
    graph.cameraPosition(
      { x: n.x * distRatio, y: n.y * distRatio, z: n.z * distRatio },
      { x: n.x, y: n.y, z: n.z },
      1000,
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">필터:</span>
        <button
          onClick={() => setActiveType('all')}
          className={'text-xs px-2 py-1 rounded border ' + (activeType === 'all'
            ? 'border-brand-500 text-brand-500'
            : 'border-surface-border text-slate-400 hover:text-white')}
        >
          전체 ({objects.length})
        </button>
        {types.map((t) => (
          <button
            key={t}
            onClick={() => setActiveType(t)}
            className={'text-xs px-2 py-1 rounded border flex items-center gap-1.5 ' + (activeType === t
              ? 'border-brand-500 text-brand-500'
              : 'border-surface-border text-slate-400 hover:text-white')}
          >
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: TYPE_COLOR[t] ?? '#94a3b8' }}
            />
            {t} ({objects.filter((o) => o.type === t).length})
          </button>
        ))}
        <span className="ml-auto text-xs text-slate-500">
          드래그 회전 · 휠 줌 · 노드 클릭으로 포커스
        </span>
      </div>

      <div
        ref={containerRef}
        className="relative w-full h-[600px] rounded-lg overflow-hidden border border-surface-border bg-[#0b1220]"
      >
        <ForceGraph3D
          ref={graphRef}
          graphData={data}
          width={dims.width}
          height={dims.height}
          backgroundColor={BG_COLOR}
          nodeColor={(n: any) => n.color}
          nodeVal={(n: any) => n.val}
          nodeLabel={(n: any) => `<span style="color:${LABEL_COLOR};font-family:Pretendard,sans-serif;font-size:12px">${n.name}<br/><span style='color:${n.color}'>${n.type}</span></span>`}
          nodeThreeObject={(n: any) => {
            const geom = new THREE.SphereGeometry(n.val, 16, 16)
            const mat = new THREE.MeshStandardMaterial({
              color: n.color,
              emissive: new THREE.Color(n.color).multiplyScalar(0.35),
              roughness: 0.4,
              metalness: 0.6,
            })
            return new THREE.Mesh(geom, mat)
          }}
          linkColor={() => LINK_COLOR}
          linkOpacity={0.5}
          linkWidth={0.6}
          linkDirectionalParticles={1}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={0.008}
          linkLabel={(l: any) => l.predicate}
          onNodeClick={(n: any) => {
            setHoveredNode(n)
            focusOnNode(n)
          }}
          onNodeHover={(n: any) => setHoveredNode(n)}
          enableNodeDrag={true}
        />

        {hoveredNode && (
          <div className="absolute top-3 left-3 bg-surface-card/90 backdrop-blur border border-surface-border rounded p-3 text-xs max-w-xs">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="inline-block w-2.5 h-2.5 rounded-full"
                style={{ background: hoveredNode.color }}
              />
              <span className="text-slate-500">{hoveredNode.type}</span>
            </div>
            <div className="text-sm font-semibold text-white">{hoveredNode.name}</div>
            <div className="text-slate-500 mt-1 font-mono">{hoveredNode.id}</div>
          </div>
        )}

        <div className="absolute bottom-3 right-3 text-[10px] text-slate-600 bg-surface-card/70 backdrop-blur px-2 py-1 rounded">
          nodes {data.nodes.length} · edges {data.links.length}
        </div>
      </div>
    </div>
  )
}
