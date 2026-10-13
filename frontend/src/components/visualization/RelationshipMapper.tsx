import { useState, useMemo } from 'react'
import {
  GitFork,
  Database,
  Key,
  Target,
  ArrowRight,
  Search,
  Sparkles
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface RelationshipNode {
  id: string
  label: string
  type: 'table' | 'column'
  role?: string
  dataType?: string
  isUnique?: boolean
  rowCount?: number
  nullCount?: number
  parentTable?: string
}

interface RelationshipEdge {
  id: string
  source: string
  target: string
  sourceLabel: string
  targetLabel: string
  predicate: string
  cardinality?: string
  confidence?: number
  kind?: 'structural' | 'causal' | 'relational'
  joinKey?: string
  description?: string
}

interface RelationshipMapperProps {
  nodes?: RelationshipNode[]
  relationships?: RelationshipEdge[]
  datasetName?: string
  className?: string
}

export default function RelationshipMapper({
  nodes = [],
  relationships = [],
  datasetName = 'Active Dataset',
  className = '',
}: RelationshipMapperProps) {
  const [filterKind, setFilterKind] = useState<'all' | 'relational' | 'causal' | 'structural'>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  // Filtered relationships
  const filteredRelationships = useMemo(() => {
    return relationships.filter((rel) => {
      const matchKind = filterKind === 'all' || rel.kind === filterKind
      const matchSearch =
        !searchQuery.trim() ||
        rel.sourceLabel.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rel.targetLabel.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rel.predicate.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (rel.description && rel.description.toLowerCase().includes(searchQuery.toLowerCase()))
      return matchKind && matchSearch
    })
  }, [relationships, filterKind, searchQuery])

  // Selected node details
  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId)
  }, [nodes, selectedNodeId])

  // Count by kind
  const counts = useMemo(() => {
    const relational = relationships.filter((r) => r.kind === 'relational').length
    const causal = relationships.filter((r) => r.kind === 'causal').length
    const structural = relationships.filter((r) => r.kind === 'structural').length
    return { all: relationships.length, relational, causal, structural }
  }, [relationships])

  // Node position map for SVG graph rendering
  const graphLayout = useMemo(() => {
    const W = 800
    const H = 420
    const tableNodes = nodes.filter((n) => n.type === 'table')
    const colNodes = nodes.filter((n) => n.type === 'column')

    const pos = new Map<string, { x: number; y: number }>()

    // Place main table on the left / center-left
    tableNodes.forEach((t, idx) => {
      pos.set(t.id, {
        x: 120 + idx * 260,
        y: 80,
      })
    })

    // Place columns in radial arc or grid around
    colNodes.forEach((c, idx) => {
      const colsPerRow = 4
      const row = Math.floor(idx / colsPerRow)
      const col = idx % colsPerRow
      const x = 70 + col * 180
      const y = 200 + row * 90
      pos.set(c.id, { x, y })
    })

    return { pos, W, H }
  }, [nodes])

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Overview Metric Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-card/70 border shadow-sm">
          <CardHeader className="pb-1 pt-3.5 px-4">
            <CardDescription className="text-xs flex items-center justify-between">
              Spotted Entities <Database className="h-4 w-4 text-primary" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold mt-1">
              {nodes.filter((n) => n.type === 'table').length || 1}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-0 text-[11px] text-muted-foreground">
            Tables & extracted datasets
          </CardContent>
        </Card>

        <Card className="bg-card/70 border shadow-sm">
          <CardHeader className="pb-1 pt-3.5 px-4">
            <CardDescription className="text-xs flex items-center justify-between">
              Mapped Columns <Key className="h-4 w-4 text-emerald-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold mt-1">
              {nodes.filter((n) => n.type === 'column').length}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-0 text-[11px] text-muted-foreground">
            Keys, metrics & dimensions
          </CardContent>
        </Card>

        <Card className="bg-card/70 border shadow-sm">
          <CardHeader className="pb-1 pt-3.5 px-4">
            <CardDescription className="text-xs flex items-center justify-between">
              Target Drivers <Target className="h-4 w-4 text-indigo-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold mt-1">{counts.causal}</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-0 text-[11px] text-muted-foreground">
            Feature outcome mappings
          </CardContent>
        </Card>

        <Card className="bg-card/70 border shadow-sm">
          <CardHeader className="pb-1 pt-3.5 px-4">
            <CardDescription className="text-xs flex items-center justify-between">
              Foreign Key Links <GitFork className="h-4 w-4 text-amber-500" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold mt-1">{counts.relational}</CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-0 text-[11px] text-muted-foreground">
            Cross-dataset matchings
          </CardContent>
        </Card>
      </div>

      {/* Visual Interactive SVG Relationship Graph */}
      <Card className="overflow-hidden border shadow-sm bg-card">
        <CardHeader className="bg-muted/20 border-b pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-bold flex items-center gap-2">
              <GitFork className="h-4 w-4 text-primary" />
              Entity-Relationship & Feature Dependency Graph
            </CardTitle>
            <CardDescription className="text-xs">
              Interactive structural and foreign-key link visualizer for {datasetName}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-blue-500" /> Table
            </span>
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> Primary Key
            </span>
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-amber-500" /> Foreign Key
            </span>
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-indigo-500" /> Target
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-2 sm:p-4 bg-slate-900/40 relative">
          <div className="w-full overflow-x-auto">
            <svg
              viewBox={`0 0 ${graphLayout.W} ${graphLayout.H}`}
              className="w-full min-w-[700px] h-[340px] select-none"
            >
              <defs>
                <marker
                  id="relArrow"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                </marker>
                <marker
                  id="relArrowActive"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#3b82f6" />
                </marker>
              </defs>

              {/* Render Relationships (Edges) */}
              {relationships.map((rel) => {
                const sPos = graphLayout.pos.get(rel.source)
                const tPos = graphLayout.pos.get(rel.target)
                if (!sPos || !tPos) return null

                const isConnected =
                  selectedNodeId &&
                  (rel.source === selectedNodeId || rel.target === selectedNodeId)

                return (
                  <g key={rel.id}>
                    <line
                      x1={sPos.x + 40}
                      y1={sPos.y + 15}
                      x2={tPos.x + 40}
                      y2={tPos.y + 15}
                      stroke={isConnected ? '#3b82f6' : rel.kind === 'causal' ? '#818cf8' : '#64748b'}
                      strokeWidth={isConnected ? 2.5 : 1.5}
                      strokeDasharray={rel.kind === 'causal' ? '4 3' : undefined}
                      strokeOpacity={isConnected ? 1 : 0.45}
                      markerEnd={isConnected ? 'url(#relArrowActive)' : 'url(#relArrow)'}
                    />
                    {/* Cardinality Badge on Edge */}
                    {rel.cardinality && (
                      <text
                        x={(sPos.x + tPos.x) / 2 + 40}
                        y={(sPos.y + tPos.y) / 2 + 10}
                        textAnchor="middle"
                        className="text-[9px] font-mono font-bold fill-slate-400"
                      >
                        {rel.cardinality}
                      </text>
                    )}
                  </g>
                )
              })}

              {/* Render Nodes */}
              {nodes.map((node) => {
                const pos = graphLayout.pos.get(node.id)
                if (!pos) return null

                const isSelected = selectedNodeId === node.id
                const isTable = node.type === 'table'

                let badgeColor = '#3b82f6'
                if (node.role?.includes('Primary Key')) badgeColor = '#10b981'
                else if (node.role?.includes('Foreign Key')) badgeColor = '#f59e0b'
                else if (node.role?.includes('Target')) badgeColor = '#6366f1'
                else if (node.role?.includes('Temporal')) badgeColor = '#ec4899'

                return (
                  <g
                    key={node.id}
                    className="cursor-pointer transition-transform hover:scale-105"
                    onClick={() => setSelectedNodeId(isSelected ? null : node.id)}
                  >
                    <rect
                      x={pos.x}
                      y={pos.y}
                      width={isTable ? 170 : 140}
                      height={isTable ? 48 : 34}
                      rx={8}
                      fill={isTable ? '#1e293b' : isSelected ? '#1e293b' : '#0f172a'}
                      stroke={isSelected ? '#38bdf8' : isTable ? '#3b82f6' : badgeColor}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      filter="drop-shadow(0 2px 4px rgba(0,0,0,0.3))"
                    />

                    {/* Node Label */}
                    <text
                      x={pos.x + 12}
                      y={pos.y + (isTable ? 22 : 18)}
                      className="text-xs font-bold fill-slate-100 select-none"
                    >
                      {node.label.length > 18 ? node.label.slice(0, 16) + '...' : node.label}
                    </text>

                    {/* Node Role / Subtext */}
                    <text
                      x={pos.x + 12}
                      y={pos.y + (isTable ? 38 : 28)}
                      className="text-[9px] font-mono fill-slate-400 select-none"
                    >
                      {isTable
                        ? `${node.rowCount || 0} rows • table`
                        : `${node.dataType || 'col'} • ${node.role?.slice(0, 14)}`}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>

          {/* Node Inspector Callout on Click */}
          {selectedNode && (
            <div className="mt-3 p-3 bg-background/90 backdrop-blur-sm border rounded-lg text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-md animate-in fade-in">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-foreground">{selectedNode.label}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {selectedNode.role || selectedNode.type}
                  </Badge>
                  {selectedNode.isUnique && (
                    <Badge className="bg-emerald-600 text-white text-[10px]">Unique / Primary</Badge>
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Data Type: <span className="font-mono">{selectedNode.dataType || 'N/A'}</span> •
                  Nulls: <span className="font-mono">{selectedNode.nullCount ?? 0}</span>
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={() => setSelectedNodeId(null)} className="h-7 text-xs">
                Clear Selection
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filterable Relationship Catalog Table */}
      <Card className="border shadow-sm">
        <CardHeader className="pb-3 border-b">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-emerald-500" />
                Spotted Relationship Matrix ({filteredRelationships.length})
              </CardTitle>
              <CardDescription className="text-xs">
                Auto-inferred semantic, structural, and foreign key connections
              </CardDescription>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1.5 bg-muted/50 p-1 rounded-lg border text-xs">
              <button
                onClick={() => setFilterKind('all')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  filterKind === 'all' ? 'bg-background text-foreground shadow' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                All ({counts.all})
              </button>
              <button
                onClick={() => setFilterKind('relational')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  filterKind === 'relational' ? 'bg-amber-500/20 text-amber-600 shadow' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Foreign Keys ({counts.relational})
              </button>
              <button
                onClick={() => setFilterKind('causal')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  filterKind === 'causal' ? 'bg-indigo-500/20 text-indigo-600 shadow' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Target Drivers ({counts.causal})
              </button>
              <button
                onClick={() => setFilterKind('structural')}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                  filterKind === 'structural' ? 'bg-blue-500/20 text-blue-600 shadow' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Structural ({counts.structural})
              </button>
            </div>
          </div>

          {/* Search bar */}
          <div className="relative mt-2">
            <Search className="h-3.5 w-3.5 absolute left-3 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search relationships by column, table, predicate..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-background border rounded-md pl-9 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/40 border-b text-[11px] font-semibold text-muted-foreground uppercase">
                <tr>
                  <th className="px-4 py-3">Source Entity</th>
                  <th className="px-4 py-3">Predicate</th>
                  <th className="px-4 py-3">Target Entity</th>
                  <th className="px-4 py-3">Cardinality</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Context / Description</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredRelationships.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-muted-foreground text-xs">
                      No matching relationships found.
                    </td>
                  </tr>
                ) : (
                  filteredRelationships.map((r) => (
                    <tr key={r.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3 font-semibold text-foreground flex items-center gap-1.5">
                        <Key className="h-3 w-3 text-primary shrink-0" />
                        <span>{r.sourceLabel}</span>
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-emerald-600 dark:text-emerald-400">
                        {r.predicate}
                      </td>
                      <td className="px-4 py-3 font-semibold text-foreground">
                        <span className="flex items-center gap-1.5">
                          <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                          <span>{r.targetLabel}</span>
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] font-bold text-muted-foreground">
                        <span className="px-1.5 py-0.5 rounded bg-muted">
                          {r.cardinality || '1:N'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            (r.confidence || 0) >= 0.9
                              ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                              : 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                          }`}
                        >
                          {Math.round((r.confidence || 0.8) * 100)}%
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground max-w-xs truncate">
                        {r.description || 'Relationship inferred from DuckDB schema profiling.'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
