import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertCircle, Wand2, ArrowRight, ShieldAlert, CheckCircle, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

export default function HealingUI() {
  const { projectId } = useParams<{ projectId: string }>()
  const [datasets, setDatasets] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [plan, setPlan] = useState<any>(null)
  const [applying, setApplying] = useState(false)
  const [healingEvent, setHealingEvent] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const [pastEvents, setPastEvents] = useState<any[]>([])

  const loadPastEvents = (dsId: string) => {
    if (!dsId) return
    api.healing.listEvents(dsId).then(res => {
      setPastEvents(res.events || [])
    }).catch(() => setPastEvents([]))
  }

  useEffect(() => {
    if (projectId) {
      api.datasets.list(projectId).then(ds => {
        setDatasets(ds)
        if (ds.length > 0) {
          const firstId = ds[0].dataset_id || ds[0].id
          setSelectedDatasetId(firstId)
          loadPastEvents(firstId)
        }
      })
    }
  }, [projectId])

  const handleDatasetChange = (dsId: string) => {
    setSelectedDatasetId(dsId)
    setPlan(null)
    setHealingEvent(null)
    setError(null)
    loadPastEvents(dsId)
  }

  const handleGeneratePlan = async () => {
    if (!selectedDatasetId) return
    setGenerating(true)
    setError(null)
    setPlan(null)
    setHealingEvent(null)
    try {
      const res = await api.healing.plan(selectedDatasetId)
      setPlan(res.plan)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Failed to generate healing plan.')
    } finally {
      setGenerating(false)
    }
  }

  const handleApplyHealing = async () => {
    if (!selectedDatasetId || !plan) return
    setApplying(true)
    try {
      const res = await api.healing.apply(selectedDatasetId, plan)
      setHealingEvent(res)
      loadPastEvents(selectedDatasetId)
    } catch (err: any) {
      console.error(err)
      alert(err.message || 'Failed to apply healing.')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Transformation & Healing</h2>
          <p className="text-muted-foreground">Review, simulate, and apply non-destructive autonomous data transformations.</p>
        </div>
        <div className="flex items-center gap-3">
          {datasets.length > 0 && (
            <select
              className="border rounded px-3 py-1.5 text-sm bg-background font-medium"
              value={selectedDatasetId}
              onChange={(e) => handleDatasetChange(e.target.value)}
            >
              {datasets.map(d => (
                <option key={d.id || d.dataset_id} value={d.id || d.dataset_id}>
                  {d.name || d.original_filename} ({((d.id || d.dataset_id) as string).slice(0, 8)}...)
                </option>
              ))}
            </select>
          )}
          <Button onClick={handleGeneratePlan} disabled={generating || !selectedDatasetId}>
            {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
            Generate Healing Plan
          </Button>
        </div>
      </div>

      <div className="p-4 bg-muted/40 border rounded-lg flex items-start gap-4">
        <ShieldAlert className="h-5 w-5 text-primary mt-0.5" />
        <div>
          <h4 className="font-semibold text-sm">Original Dataset is Immutable</h4>
          <p className="text-sm text-muted-foreground">
            Healing operations strictly generate a <strong>Derived Dataset</strong> stored as Parquet. The original source dataset is never overwritten or mutated.
          </p>
        </div>
      </div>

      {error && (
        <Card className="border-red-500/50 bg-red-500/5 p-4 text-red-600 font-medium">
          {error}
        </Card>
      )}

      {plan && (
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-primary" /> Autonomous Transformation Proposal
                </CardTitle>
                <CardDescription>Generated remediation plan based on real profiling results</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="border rounded-lg p-4 bg-background shadow-sm space-y-3">
                  <div>
                    <span className="text-xs uppercase text-muted-foreground font-semibold block mb-1">Detected Situation</span>
                    <p className="font-bold text-sm">{plan.problem_detected}</p>
                  </div>
                  <div>
                    <span className="text-xs uppercase text-muted-foreground font-semibold block mb-1">Remediation Proposal</span>
                    <p className="font-medium text-sm flex items-center gap-2">
                      <Wand2 className="h-4 w-4 text-primary" /> {plan.remediation_proposal}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs uppercase text-muted-foreground font-semibold block mb-1">Impact</span>
                    <p className="text-xs text-muted-foreground font-mono">{plan.estimated_impact}</p>
                  </div>
                  {plan.columns_affected && plan.columns_affected.length > 0 && (
                    <div>
                      <span className="text-xs uppercase text-muted-foreground font-semibold block mb-1">Columns Handled</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {plan.columns_affected.map((c: string, idx: number) => (
                          <span key={idx} className="bg-muted px-2 py-0.5 rounded text-xs font-mono">{c}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
              {!healingEvent && (
                <CardFooter>
                  <Button className="w-full bg-emerald-600 hover:bg-emerald-700" onClick={handleApplyHealing} disabled={applying}>
                    {applying ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
                    Execute Safe Transformation
                  </Button>
                </CardFooter>
              )}
            </Card>

            {healingEvent && (
              <Card className="border-emerald-500/40 bg-emerald-500/5">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                    <CheckCircle className="h-5 w-5" /> Derived Dataset Created
                  </CardTitle>
                  <CardDescription>Autonomous transformation safely executed</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div>
                    <span className="text-muted-foreground uppercase font-semibold block text-[10px]">Derived Dataset ID</span>
                    <span className="font-mono font-bold text-sm text-foreground">{healingEvent.derived_dataset_id}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground uppercase font-semibold block text-[10px]">Parquet Storage File</span>
                    <span className="font-mono bg-background p-2 rounded block break-all border text-foreground">
                      {healingEvent.derived_path}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quality Verification</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {healingEvent ? (
                  <div className="flex items-center justify-between">
                    <div className="text-center">
                      <p className="text-xs text-muted-foreground font-semibold uppercase">Before</p>
                      <p className="text-3xl font-bold text-orange-500">{healingEvent.quality_report?.before_score}</p>
                      <p className="text-xs text-muted-foreground mt-1">Score</p>
                    </div>
                    <ArrowRight className="h-6 w-6 text-muted-foreground" />
                    <div className="text-center">
                      <p className="text-xs text-muted-foreground font-semibold uppercase">After</p>
                      <p className="text-3xl font-bold text-emerald-600">{healingEvent.quality_report?.after_score}</p>
                      <p className="text-xs text-muted-foreground mt-1">Score</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm text-center">Execute safe transformation to view before & after quality scores.</p>
                )}
                {healingEvent?.quality_report?.improvements && (
                  <div className="border-t pt-3 text-xs space-y-1">
                    <span className="font-bold text-muted-foreground block uppercase">Improvements</span>
                    {healingEvent.quality_report.improvements.map((imp: string, i: number) => (
                      <p key={i} className="text-emerald-600 font-medium">&bull; {imp}</p>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {pastEvents.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-semibold">Transformation History ({pastEvents.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y text-xs">
                    {pastEvents.slice(0, 5).map((pe, idx) => (
                      <div key={idx} className="p-3 space-y-1">
                        <div className="flex justify-between font-mono">
                          <span className="text-emerald-600 font-semibold">{pe.derived_dataset_id?.slice(0, 8)}...</span>
                          <span className="text-muted-foreground text-[10px]">
                            {pe.timestamp ? new Date(pe.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted-foreground truncate">{pe.plan?.problem_detected}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
