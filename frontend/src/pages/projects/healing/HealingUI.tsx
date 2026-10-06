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

  useEffect(() => {
    if (projectId) {
      api.datasets.list(projectId).then(ds => {
        setDatasets(ds)
        if (ds.length > 0) setSelectedDatasetId(ds[0].dataset_id || ds[0].id)
      })
    }
  }, [projectId])

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
          <p className="text-muted-foreground">Review and approve automated data quality corrections.</p>
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
          <Button onClick={handleGeneratePlan} disabled={generating || !selectedDatasetId}>
            {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Wand2 className="mr-2 h-4 w-4" />}
            Generate Healing Plan
          </Button>
        </div>
      </div>

      <div className="p-4 bg-muted/40 border rounded-lg flex items-start gap-4">
        <ShieldAlert className="h-5 w-5 text-muted-foreground mt-0.5" />
        <div>
          <h4 className="font-semibold text-sm">Original Dataset is Immutable</h4>
          <p className="text-sm text-muted-foreground">Healing operations strictly generate a <strong>Derived Dataset</strong>. Original data is never overwritten or modified.</p>
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
                <CardTitle>Detected Issues & Remediation Proposal</CardTitle>
                <CardDescription>Safe autonomous transformation proposal</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="border rounded-lg p-4 bg-background shadow-sm space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-orange-500" />
                    <span className="font-bold">{plan.problem_detected}</span>
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
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Quality Metrics</CardTitle>
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
          </div>
        </div>
      )}
    </div>
  )
}
