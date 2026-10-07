import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CheckCircle, Clock, PlayCircle, AlertTriangle, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

export default function AgentExecutionCenter() {
  const { projectId } = useParams<{ projectId: string }>()
  const [datasets, setDatasets] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [executing, setExecuting] = useState(false)
  const [runData, setRunData] = useState<any>(null)
  const [auditEvents, setAuditEvents] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (projectId) {
      api.datasets.list(projectId).then(ds => {
        setDatasets(ds)
        if (ds.length > 0) setSelectedDatasetId(ds[0].dataset_id || ds[0].id)
      })
    }
  }, [projectId])

  const handleExecute = async () => {
    if (!projectId || !selectedDatasetId) return
    setExecuting(true)
    setError(null)
    try {
      const res = await api.runs.execute(projectId, selectedDatasetId, "Execute full transformation workflow")
      setRunData(res)
      if (res.run_id) {
        const auditRes = await api.runs.getAudit(res.run_id)
        setAuditEvents(auditRes.events || [])
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Execution failed.')
    } finally {
      setExecuting(false)
    }
  }

  const nodes = [
    { id: 'INGEST', name: 'Ingestion Agent' },
    { id: 'PROFILE', name: 'Profiling Engine' },
    { id: 'SEMANTIC_ANALYSIS', name: 'Semantic Layer' },
    { id: 'ANALYSIS_PLANNING', name: 'Data Analyst Agent' },
    { id: 'VERIFICATION', name: 'Verification Engine' },
    { id: 'MODEL_TOURNAMENT', name: 'Data Scientist Agent' },
    { id: 'ML_ENGINEER', name: 'ML Engineer Agent' },
    { id: 'AUDIT', name: 'Audit & Lineage System' },
  ]

  const getStepStatus = () => {
    if (!runData) return 'WAITING'
    const status = runData.status
    if (status === 'COMPLETED') return 'PASSED'
    if (status === 'FAILED') return 'FAILED'
    return 'PASSED'
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Agent Execution Center</h2>
          <p className="text-muted-foreground">Monitor and trigger multi-agent autonomous orchestration workflows.</p>
        </div>
        <div className="flex items-center gap-3">
          {datasets.length > 0 && (
            <select
              className="border rounded px-3 py-1.5 text-sm bg-background"
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
            >
              {datasets.map(d => (
                <option key={d.id || d.dataset_id} value={d.id || d.dataset_id}>
                  {d.name || d.original_filename} ({d.id || d.dataset_id})
                </option>
              ))}
            </select>
          )}
          <Button onClick={handleExecute} disabled={executing || !selectedDatasetId}>
            {executing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlayCircle className="mr-2 h-4 w-4" />}
            Run Workflow
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-red-500/50 bg-red-500/5 p-4 text-red-600 font-medium">
          <AlertTriangle className="h-5 w-5 inline mr-2" />
          {error}
        </Card>
      )}

      {runData && runData.status === 'PAUSED_FOR_INPUT' && (
        <Card className="border-amber-500/50 bg-amber-500/10 p-4 text-amber-800 dark:text-amber-300 font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            <span>Workflow Paused: Semantic ambiguity detected. A human decision is required.</span>
          </div>
          <Button size="sm" variant="outline" asChild>
            <Link to={`/projects/${projectId}/knowledge`}>Resolve Ambiguity</Link>
          </Button>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Execution Graph */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>LangGraph Pipeline</CardTitle>
              <CardDescription>Live execution node status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative border-l-2 border-muted ml-3 space-y-6">
                {nodes.map((node) => {
                  const st = getStepStatus()
                  return (
                    <div key={node.id} className="relative flex items-center gap-4 pl-6">
                      <div className="absolute -left-[11px] bg-background">
                        {st === 'PASSED' ? <CheckCircle className="h-5 w-5 text-emerald-500" /> : <Clock className="h-5 w-5 text-muted-foreground" />}
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{node.name}</p>
                        <p className="text-xs text-muted-foreground">{node.id}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Details & Logs */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Execution State & Audit Trail</CardTitle>
              <CardDescription>
                {runData ? `Run ID: ${runData.run_id}` : 'Click "Run Workflow" to trigger LangGraph execution.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="audit">
                <TabsList className="mb-4">
                  <TabsTrigger value="audit">Audit Events ({auditEvents.length})</TabsTrigger>
                  <TabsTrigger value="state">Raw State</TabsTrigger>
                </TabsList>

                <TabsContent value="audit">
                  {auditEvents.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-6 text-center">No audit events logged yet.</p>
                  ) : (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {auditEvents.map((ev, i) => (
                        <div key={i} className="p-3 border rounded text-xs bg-muted/20 font-mono">
                          <div className="flex justify-between font-bold text-foreground">
                            <span className="text-primary">&gt; {ev.event_type || ev.action || 'EVENT'}</span>
                            <span className="text-muted-foreground font-normal">
                              {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : (ev.timestamp || '')}
                            </span>
                          </div>
                          <div className="text-muted-foreground mt-1 flex items-center gap-2">
                            <span>Status: <strong className={ev.status === 'ok' ? 'text-emerald-500' : 'text-foreground'}>{ev.status}</strong></span>
                            {ev.dataset_id && <span>| Dataset: {ev.dataset_id.slice(0, 8)}...</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="state">
                  <pre className="bg-muted p-4 rounded text-xs font-mono max-h-96 overflow-auto">
                    {runData ? JSON.stringify(runData.state, null, 2) : '// No run state yet'}
                  </pre>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
