import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FolderOpen, Database, Bot, CheckCircle, Plus, ArrowRight, Activity, Clock } from 'lucide-react'
import { api, type Project, type Dataset } from '@/lib/api'

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.projects.list().catch(() => []),
      api.datasets.list().catch(() => []),
      api.runs.list().catch(() => [])
    ]).then(([pList, dList, rList]) => {
      setProjects(pList)
      setDatasets(dList)
      setRuns(rList)
      setLoading(false)
    })
  }, [])

  const activeRuns = runs.filter(r => r.status && !['COMPLETED', 'FAILED'].includes(r.status))
  const completedRuns = runs.filter(r => r.status === 'COMPLETED')
  const passRate = runs.length > 0
    ? Math.round((completedRuns.length / runs.length) * 100)
    : 100

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Overview</h2>
          <p className="text-muted-foreground">Platform operational status and live system activity.</p>
        </div>
        <Button asChild>
          <Link to="/projects/new">
            <Plus className="mr-2 h-4 w-4" /> New Project
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Projects</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : projects.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Active workspaces</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Datasets</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : datasets.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Ingested real Parquet tables</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agent Runs</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : activeRuns.length}</div>
            <p className="text-xs text-muted-foreground mt-1">In-flight orchestrations</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Verification Pass Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? '...' : `${passRate}%`}</div>
            <p className="text-xs text-muted-foreground mt-1">Evidence gate verification</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <h3 className="text-lg font-medium flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" /> Recent Pipeline Executions
          </h3>
          <Card>
            <CardContent className="p-6">
              {runs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p className="text-sm">No workflow runs executed yet.</p>
                  <p className="text-xs mt-1">Create a project and upload a dataset to trigger the multi-agent pipeline.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {runs.slice(0, 5).map((run, i) => (
                    <div key={run.run_id || i} className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/30 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className={`h-2.5 w-2.5 rounded-full ${run.status === 'COMPLETED' ? 'bg-emerald-500' : (run.status === 'FAILED' ? 'bg-red-500' : 'bg-amber-500')}`} />
                        <div>
                          <p className="text-sm font-medium">{run.business_goal || `Workflow Run ${run.run_id?.slice(0, 8)}`}</p>
                          <p className="text-xs text-muted-foreground">
                            Run ID: {run.run_id?.slice(0, 8)}... | Status: <span className="font-semibold">{run.status}</span>
                          </p>
                        </div>
                      </div>
                      {run.created_at && (
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-medium">Recent Projects</h3>
          <Card>
            <CardContent className="p-6 space-y-3">
              {projects.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">No projects created yet.</p>
              ) : (
                projects.slice(0, 4).map(p => (
                  <div key={p.id} className="p-3 border rounded-lg hover:border-primary/50 transition-colors">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold truncate">{p.name}</span>
                      <Button variant="ghost" size="sm" asChild className="h-7 px-2">
                        <Link to={`/projects/${p.id}`}>
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 truncate">{p.description || 'No description'}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

