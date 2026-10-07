import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Database,
  BrainCircuit,
  BarChart,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
  Upload,
  PlayCircle,
  FileCheck2,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import { api, type Project, type Dataset } from '@/lib/api'

interface ProjectOverviewProps {
  projectId: string
  onNavigateTab: (tab: string) => void
}

export default function ProjectOverview({ projectId, onNavigateTab }: ProjectOverviewProps) {
  const [project, setProject] = useState<Project | null>(null)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return
    Promise.all([
      api.projects.get(projectId).catch(() => null),
      api.datasets.list(projectId).catch(() => []),
      api.runs.list(projectId).catch(() => [])
    ]).then(([proj, dsList, rList]) => {
      setProject(proj)
      setDatasets(dsList)
      setRuns(rList)
      setLoading(false)
    })
  }, [projectId])

  const totalRows = datasets.reduce((acc, d) => acc + (d.rowCount || d.row_count || 0), 0)
  const latestRun = runs[0]

  return (
    <div className="space-y-6">
      {/* Project Banner */}
      <Card className="bg-gradient-to-r from-card to-muted/30 border-primary/20">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider bg-primary/10 text-primary">
                  {project?.status || 'Active'}
                </span>
                <span className="text-xs text-muted-foreground font-mono">ID: {projectId}</span>
              </div>
              <h2 className="text-xl font-bold mt-2">{project?.name || 'Project Workspace'}</h2>
              <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
                {project?.description || project?.businessGoal || 'Evidence-gated autonomous transformation workspace.'}
              </p>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => onNavigateTab('data')} className="gap-2">
                <Upload className="h-4 w-4" /> Upload Dataset
              </Button>
              <Button variant="outline" onClick={() => onNavigateTab('agents')} className="gap-2">
                <PlayCircle className="h-4 w-4" /> Run Agents
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center justify-between">
              Attached Datasets <Database className="h-4 w-4 text-muted-foreground" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold">{loading ? '...' : datasets.length}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground pt-0">
            {totalRows > 0 ? `${totalRows.toLocaleString()} total rows` : 'No data ingested'}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center justify-between">
              Agent Runs <BrainCircuit className="h-4 w-4 text-muted-foreground" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold">{loading ? '...' : runs.length}</CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground pt-0">
            {latestRun ? `Latest: ${latestRun.status}` : 'No executions yet'}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center justify-between">
              Verification State <ShieldCheck className="h-4 w-4 text-muted-foreground" />
            </CardDescription>
            <CardTitle className="text-2xl font-bold">
              {latestRun?.verification_results?.status === 'PASSED' ? (
                <span className="text-emerald-500 flex items-center gap-1 text-lg">Passed</span>
              ) : (
                <span className="text-muted-foreground text-lg">Ready</span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground pt-0">
            Evidence-gated checks
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-xs flex items-center justify-between">
              Model Tournament <Cpu className="h-4 w-4 text-muted-foreground" />
            </CardDescription>
            <CardTitle className="text-lg font-bold truncate">
              {latestRun?.selected_model?.model_type || 'Pending'}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground pt-0">
            Automated benchmark
          </CardContent>
        </Card>
      </div>

      {/* Workspace Hub Actions */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Workspace Modules</h3>
        <div className="grid md:grid-cols-3 gap-4">
          <Card className="hover:border-primary/50 transition-all cursor-pointer" onClick={() => onNavigateTab('data')}>
            <CardHeader className="pb-3">
              <div className="h-8 w-8 rounded-lg bg-blue-500/10 text-blue-500 flex items-center justify-center mb-1">
                <Database className="h-4 w-4" />
              </div>
              <CardTitle className="text-base">Data Management</CardTitle>
              <CardDescription className="text-xs">
                Upload CSV/Parquet files, inspect DuckDB schemas, and review profiling distributions.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <span className="text-xs font-semibold text-primary flex items-center gap-1">
                Open Data Explorer <ArrowRight className="h-3 w-3" />
              </span>
            </CardContent>
          </Card>

          <Card className="hover:border-primary/50 transition-all cursor-pointer" onClick={() => onNavigateTab('knowledge')}>
            <CardHeader className="pb-3">
              <div className="h-8 w-8 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center mb-1">
                <Layers className="h-4 w-4" />
              </div>
              <CardTitle className="text-base">Semantic Knowledge</CardTitle>
              <CardDescription className="text-xs">
                Review semantic ontology, dimensional mappings, and resolve ambiguity breakpoints.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <span className="text-xs font-semibold text-primary flex items-center gap-1">
                View Knowledge Layer <ArrowRight className="h-3 w-3" />
              </span>
            </CardContent>
          </Card>

          <Card className="hover:border-primary/50 transition-all cursor-pointer" onClick={() => onNavigateTab('agents')}>
            <CardHeader className="pb-3">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center mb-1">
                <BrainCircuit className="h-4 w-4" />
              </div>
              <CardTitle className="text-base">Autonomous Orchestrator</CardTitle>
              <CardDescription className="text-xs">
                Trigger full LangGraph 8-stage transformation pipelines with live execution audit tracking.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <span className="text-xs font-semibold text-primary flex items-center gap-1">
                Run Agent Workflows <ArrowRight className="h-3 w-3" />
              </span>
            </CardContent>
          </Card>

          <Card className="hover:border-primary/50 transition-all cursor-pointer" onClick={() => onNavigateTab('analysis')}>
            <CardHeader className="pb-3">
              <div className="h-8 w-8 rounded-lg bg-amber-500/10 text-amber-500 flex items-center justify-center mb-1">
                <BarChart className="h-4 w-4" />
              </div>
              <CardTitle className="text-base">Data Analyst Agent</CardTitle>
              <CardDescription className="text-xs">
                Ask analytical questions in natural language and receive real DuckDB KPI aggregations.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <span className="text-xs font-semibold text-primary flex items-center gap-1">
                Query & Analyze <ArrowRight className="h-3 w-3" />
              </span>
            </CardContent>
          </Card>

          <Card className="hover:border-primary/50 transition-all cursor-pointer" onClick={() => onNavigateTab('models')}>
            <CardHeader className="pb-3">
              <div className="h-8 w-8 rounded-lg bg-purple-500/10 text-purple-500 flex items-center justify-center mb-1">
                <Cpu className="h-4 w-4" />
              </div>
              <CardTitle className="text-base">Model Tournament</CardTitle>
              <CardDescription className="text-xs">
                Run multi-model training tournaments on real dataset tables with automatic feature selection.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <span className="text-xs font-semibold text-primary flex items-center gap-1">
                Launch Tournament <ArrowRight className="h-3 w-3" />
              </span>
            </CardContent>
          </Card>

          <Card className="hover:border-primary/50 transition-all cursor-pointer" onClick={() => onNavigateTab('audit')}>
            <CardHeader className="pb-3">
              <div className="h-8 w-8 rounded-lg bg-rose-500/10 text-rose-500 flex items-center justify-center mb-1">
                <FileCheck2 className="h-4 w-4" />
              </div>
              <CardTitle className="text-base">Audit & Lineage</CardTitle>
              <CardDescription className="text-xs">
                Inspect immutable cryptographic event trails and provenance for compliance verification.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <span className="text-xs font-semibold text-primary flex items-center gap-1">
                View Audit Trail <ArrowRight className="h-3 w-3" />
              </span>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Datasets Table */}
      {datasets.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Attached Datasets</CardTitle>
            <CardDescription className="text-xs">Real DuckDB tables registered for this workspace</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="p-3 font-semibold">Dataset Name</th>
                    <th className="p-3 font-semibold">Format</th>
                    <th className="p-3 font-semibold">Rows</th>
                    <th className="p-3 font-semibold">Columns</th>
                    <th className="p-3 font-semibold">Status</th>
                    <th className="p-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {datasets.map((d) => (
                    <tr key={d.id} className="border-b last:border-0 hover:bg-muted/20">
                      <td className="p-3 font-medium">{d.name}</td>
                      <td className="p-3 uppercase text-muted-foreground">{d.format || 'csv'}</td>
                      <td className="p-3 font-mono">{(d.rowCount || d.row_count || 0).toLocaleString()}</td>
                      <td className="p-3 font-mono">{d.columnCount || d.column_count || '-'}</td>
                      <td className="p-3">
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold">
                          <CheckCircle2 className="h-3 w-3" /> Ready
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <Button variant="ghost" size="sm" asChild className="h-7 text-xs">
                          <Link to={`/projects/${projectId}/data/${d.id}`}>Explore</Link>
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
