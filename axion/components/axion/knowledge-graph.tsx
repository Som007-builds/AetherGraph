'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import useSWR from 'swr'
import { Loader2, Network, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { getGraphData } from '@/lib/api-client'
import type { GraphData, GraphNode, GraphEdge } from '@/types/axion'

// Dynamic import for react-force-graph-2d (needs window/canvas)
import dynamic from 'next/dynamic'
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
  loading: () => (
    <div className="flex h-[500px] items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-[#3b9eff]" />
    </div>
  ),
})

// ─── Color helpers ───────────────────────────────────────────────────────────

function getNodeColor(node: GraphNode): string {
  switch (node.type) {
    case 'paper':
      return '#3b9eff' // electric blue
    case 'claim': {
      const c = node.confidence ?? 0.5
      if (c >= 0.8) return '#3ad389'   // green — high
      if (c >= 0.5) return '#ffca16'   // yellow — medium
      return '#ff9592'                  // red — low
    }
    case 'gap':
      return '#9281f7' // violet
    default:
      return '#6c6c6c'
  }
}

function getNodeSize(node: GraphNode): number {
  switch (node.type) {
    case 'paper': return 6
    case 'claim': return 4
    case 'gap':   return 5
    default:      return 3
  }
}

function getEdgeColor(edge: { type?: string }): string {
  switch (edge.type) {
    case 'CONTRADICTS': return 'rgba(255, 149, 146, 0.6)'  // red
    case 'SUPPORTS':    return 'rgba(58, 211, 137, 0.4)'   // green
    case 'RELATES_TO':  return 'rgba(146, 129, 247, 0.4)'  // violet
    default:            return 'rgba(108, 108, 108, 0.25)'  // dim gray
  }
}

function getEdgeWidth(edge: { type?: string }): number {
  return edge.type === 'CONTRADICTS' ? 1.8 : 0.8
}

// ─── Legend ──────────────────────────────────────────────────────────────────

function Legend() {
  const nodeItems = [
    { color: '#3b9eff', label: 'Paper' },
    { color: '#3ad389', label: 'Claim (High)' },
    { color: '#ffca16', label: 'Claim (Med)' },
    { color: '#ff9592', label: 'Claim (Low)' },
    { color: '#9281f7', label: 'Gap' },
  ]
  const edgeItems = [
    { color: '#ff9592', label: 'Contradicts', style: 'solid' },
    { color: '#6c6c6c', label: 'Extracted From', style: 'dashed' },
  ]

  return (
    <div className="absolute bottom-4 left-4 z-10 rounded-lg border border-[#292d30] bg-black/80 p-3 backdrop-blur-sm">
      <p className="mb-2 text-xs font-medium text-[#a1a4a5]">Nodes</p>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {nodeItems.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-[10px] text-[#a1a4a5]">{item.label}</span>
          </div>
        ))}
      </div>
      <p className="mb-1 mt-2 text-xs font-medium text-[#a1a4a5]">Edges</p>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {edgeItems.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span
              className="inline-block h-0.5 w-4"
              style={{
                backgroundColor: item.color,
                borderStyle: item.style === 'dashed' ? 'dashed' : 'solid',
              }}
            />
            <span className="text-[10px] text-[#a1a4a5]">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function KnowledgeGraph() {
  const [claimLimit, setClaimLimit] = useState(100)
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })

  const {
    data: graphData,
    isLoading,
    error,
  } = useSWR<GraphData>(
    `graph-data-${claimLimit}`,
    () => getGraphData(claimLimit),
    { revalidateOnFocus: false }
  )

  // Responsive sizing
  useEffect(() => {
    function updateSize() {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({ width: rect.width, height: Math.max(500, rect.height) })
      }
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  // Zoom-to-fit after data loads
  useEffect(() => {
    if (graphData && graphRef.current) {
      const timer = setTimeout(() => {
        graphRef.current?.zoomToFit(400, 60)
      }, 800)
      return () => clearTimeout(timer)
    }
  }, [graphData])

  const handleZoomIn = useCallback(() => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom()
      graphRef.current.zoom(currentZoom * 1.4, 300)
    }
  }, [])

  const handleZoomOut = useCallback(() => {
    if (graphRef.current) {
      const currentZoom = graphRef.current.zoom()
      graphRef.current.zoom(currentZoom / 1.4, 300)
    }
  }, [])

  const handleZoomToFit = useCallback(() => {
    graphRef.current?.zoomToFit(400, 60)
  }, [])

  // Transform data for react-force-graph (it expects { id } nodes and { source, target } links)
  // Filter out edges whose source/target nodes weren't loaded (due to claim limit)
  const fgData = (() => {
    if (!graphData) return { nodes: [], links: [] }
    const nodeIds = new Set(graphData.nodes.map((n) => n.id))
    return {
      nodes: graphData.nodes.map((n) => ({ ...n })),
      links: graphData.edges
        .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
        .map((e) => ({
          source: e.source,
          target: e.target,
          type: e.type,
        })),
    }
  })()

  return (
    <div className="space-y-4">
      {/* Controls bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Network className="h-5 w-5 text-[#3b9eff]" />
          <h3 className="text-lg font-medium text-[#f0f0f0]">
            Knowledge Graph
          </h3>
          {graphData && (
            <Badge
              variant="outline"
              className="border-[#292d30] bg-transparent text-xs text-[#6c6c6c]"
            >
              {graphData.nodes.length} nodes · {graphData.edges.length} edges
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Claim limit slider */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#6c6c6c]">Claims:</span>
            <div className="w-28">
              <Slider
                defaultValue={[claimLimit]}
                min={25}
                max={200}
                step={25}
                onValueCommit={(val: number[]) => setClaimLimit(val[0])}
              />
            </div>
            <span className="w-8 text-right font-mono text-xs text-[#a1a4a5]">
              {claimLimit}
            </span>
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7 border-[#292d30] bg-transparent text-[#a1a4a5] hover:border-[#3b9eff] hover:text-[#f0f0f0]"
              onClick={handleZoomIn}
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7 border-[#292d30] bg-transparent text-[#a1a4a5] hover:border-[#3b9eff] hover:text-[#f0f0f0]"
              onClick={handleZoomOut}
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7 border-[#292d30] bg-transparent text-[#a1a4a5] hover:border-[#3b9eff] hover:text-[#f0f0f0]"
              onClick={handleZoomToFit}
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-[#ff9592]/30 bg-[#ff9592]/5 p-4">
          <p className="text-sm text-[#ff9592]">
            Failed to load graph data. Is the API running on port 8000?
          </p>
        </div>
      )}

      {/* Graph canvas */}
      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-xl border border-[#292d30] bg-[#050508]"
        style={{ height: 560 }}
      >
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="space-y-3 text-center">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-[#3b9eff]" />
              <p className="text-sm text-[#6c6c6c]">Loading graph data…</p>
            </div>
          </div>
        ) : graphData && graphData.nodes.length > 0 ? (
          <>
            <ForceGraph2D
              ref={graphRef}
              graphData={fgData}
              width={dimensions.width}
              height={560}
              backgroundColor="#050508"
              nodeRelSize={1}
              nodeVal={(node: GraphNode) => getNodeSize(node) ** 2}
              nodeColor={(node: GraphNode) => getNodeColor(node)}
              nodeLabel=""
              linkColor={(link: { type?: string }) => getEdgeColor(link)}
              linkWidth={(link: { type?: string }) => getEdgeWidth(link)}
              linkDirectionalArrowLength={3}
              linkDirectionalArrowRelPos={1}
              linkDirectionalArrowColor={(link: { type?: string }) => getEdgeColor(link)}
              cooldownTicks={120}
              onNodeHover={(node: GraphNode | null) => setHoveredNode(node)}
              enableNodeDrag={true}
              enableZoomInteraction={true}
              nodeCanvasObject={(node: GraphNode & { x?: number; y?: number }, ctx: CanvasRenderingContext2D, globalScale: number) => {
                const size = getNodeSize(node) / globalScale * 2
                const color = getNodeColor(node)
                const x = node.x ?? 0
                const y = node.y ?? 0

                // Glow effect for papers
                if (node.type === 'paper') {
                  ctx.beginPath()
                  ctx.arc(x, y, size + 2, 0, 2 * Math.PI)
                  ctx.fillStyle = `${color}22`
                  ctx.fill()
                }

                // Main circle
                ctx.beginPath()
                ctx.arc(x, y, size, 0, 2 * Math.PI)
                ctx.fillStyle = color
                ctx.fill()

                // Border
                ctx.strokeStyle = `${color}88`
                ctx.lineWidth = 0.3
                ctx.stroke()

                // Label at high zoom
                if (globalScale > 2.5 && node.label) {
                  ctx.font = `${Math.max(2, 10 / globalScale)}px Inter, sans-serif`
                  ctx.textAlign = 'center'
                  ctx.textBaseline = 'top'
                  ctx.fillStyle = '#a1a4a5'
                  ctx.fillText(
                    node.label.length > 25 ? node.label.slice(0, 25) + '…' : node.label,
                    x,
                    y + size + 2
                  )
                }
              }}
            />
            <Legend />
          </>
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <Network className="mx-auto h-10 w-10 text-[#6c6c6c]" />
              <p className="mt-3 text-sm text-[#a1a4a5]">
                No graph data available
              </p>
              <p className="mt-1 text-xs text-[#6c6c6c]">
                Ingest some papers first to populate the knowledge graph
              </p>
            </div>
          </div>
        )}

        {/* Hover tooltip */}
        {hoveredNode && (
          <div className="absolute right-4 top-4 z-20 max-w-xs rounded-lg border border-[#292d30] bg-black/90 p-3 backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: getNodeColor(hoveredNode) }}
              />
              <Badge
                variant="outline"
                className="border-[#292d30] bg-transparent text-[10px] uppercase text-[#6c6c6c]"
              >
                {hoveredNode.type}
              </Badge>
            </div>
            <p className="mt-2 text-sm text-[#f0f0f0] leading-snug">
              {hoveredNode.label}
            </p>
            {hoveredNode.confidence !== undefined && (
              <p className="mt-1 text-xs text-[#6c6c6c]">
                Confidence:{' '}
                <span className="font-mono text-[#a1a4a5]">
                  {Math.round(hoveredNode.confidence * 100)}%
                </span>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
