import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { CheckCircle, BrainCircuit, BarChart, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

export default function DataAnalystWorkspace() {
  const { projectId } = useParams<{ projectId: string }>()
  const [query, setQuery] = useState('')
  const [datasets, setDatasets] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [plan, setPlan] = useState<any>(null)
  const [executing, setExecuting] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (projectId) {
      api.datasets.list(projectId).then(ds => {
        setDatasets(ds)
        if (ds.length > 0) setSelectedDatasetId(ds[0].dataset_id || ds[0].id)
      })
    }
  }, [projectId])

  const handleGeneratePlan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || !selectedDatasetId) return
    setGenerating(true)
    setError(null)
    setPlan(null)
    setResults(null)
    try {
      const res = await api.analysis.plan(selectedDatasetId, query)
      setPlan(res.plan)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Failed to generate analysis plan.')
    } finally {
      setGenerating(false)
    }
  }

  const handleExecutePlan = async () => {
    if (!selectedDatasetId || !plan) return
    setExecuting(true)
    try {
      const res = await api.analysis.execute(selectedDatasetId, plan)
      setResults(res.results)
    } catch (err: any) {
      console.error(err)
      alert(err.message || 'Analysis execution failed.')
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Data Analyst Workspace</h2>
        <p className="text-muted-foreground">Collaborate with the Data Analyst Agent to query and understand your datasets.</p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleGeneratePlan} className="space-y-4">
            {datasets.length > 0 && (
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium">Dataset:</span>
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
              </div>
            )}
            <div className="flex gap-4">
              <Input
                placeholder="What do you want to analyze? (e.g. Analyze customer churn and spend by region)"
                value={query}
                onChange={e => setQuery(e.target.value)}
                className="text-lg py-6"
              />
              <Button type="submit" size="lg" className="px-8" disabled={generating || !selectedDatasetId}>
                {generating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <BrainCircuit className="h-4 w-4 mr-2" />}
                Analyze
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-red-500/50 bg-red-500/5 p-4 text-red-600 font-medium">
          {error}
        </Card>
      )}

      {plan && (
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-1 space-y-6">
            <Card className="border-primary/30">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><BarChart className="h-4 w-4" /> Proposed Analysis Plan</CardTitle>
                <CardDescription>Deterministic plan generated from goal</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <span className="font-semibold block">Objective:</span>
                  <p className="text-muted-foreground">{plan.objective || query}</p>
                </div>
                <div>
                  <span className="font-semibold block">Target Metrics:</span>
                  <p className="text-muted-foreground font-mono text-xs">{plan.metrics?.join(', ') || 'None'}</p>
                </div>
                <div>
                  <span className="font-semibold block">Dimensions:</span>
                  <p className="text-muted-foreground font-mono text-xs">{plan.dimensions?.join(', ') || 'None'}</p>
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full" onClick={handleExecutePlan} disabled={executing}>
                  {executing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle className="h-4 w-4 mr-2" />}
                  Execute Analysis Plan
                </Button>
              </CardFooter>
            </Card>
          </div>

          <div className="md:col-span-2 space-y-6">
            {!results ? (
              <div className="h-full flex items-center justify-center border border-dashed rounded-lg text-muted-foreground p-12 text-center">
                Click "Execute Analysis Plan" to run DuckDB calculations on your dataset.
              </div>
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle>Execution Results & Provenance</CardTitle>
                  <CardDescription>Computed deterministically via DuckDB</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 border rounded bg-muted/20">
                    <span className="text-xs font-semibold text-muted-foreground uppercase block mb-2">Executive Summary</span>
                    <p className="text-sm font-medium">{results.summary || 'Analysis executed successfully.'}</p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-muted-foreground uppercase block mb-2">Raw Metrics Output</span>
                    <pre className="bg-muted p-4 rounded text-xs font-mono max-h-64 overflow-auto">
                      {JSON.stringify(results, null, 2)}
                    </pre>
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
