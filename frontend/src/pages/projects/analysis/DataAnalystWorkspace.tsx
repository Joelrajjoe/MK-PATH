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
                <CardContent className="space-y-6">
                  {/* Executive Summary */}
                  <div className="p-4 border rounded-lg bg-primary/5 border-primary/20">
                    <span className="text-xs font-semibold text-primary uppercase tracking-wider block mb-1">Executive Summary</span>
                    <p className="text-sm font-medium text-foreground leading-relaxed">
                      {results.summary || results.executive_summary || 'Analysis executed successfully.'}
                    </p>
                  </div>

                  {/* Filtered Results Highlight */}
                  {results.filtered_results && results.filtered_results.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">Filtered Findings</span>
                      <div className="grid sm:grid-cols-2 gap-3">
                        {results.filtered_results.map((fr: any, idx: number) => (
                          <div key={idx} className="p-4 border rounded-lg bg-emerald-500/5 border-emerald-500/20">
                            <span className="text-xs font-semibold text-emerald-600 block">{fr.filter}</span>
                            <div className="mt-2 space-y-1">
                              {Object.entries(fr.results || {}).map(([k, v]: [string, any]) => (
                                <div key={k} className="flex justify-between text-xs">
                                  <span className="capitalize text-muted-foreground">{k.replace(/_/g, ' ')}:</span>
                                  <span className="font-semibold">{typeof v === 'number' ? v.toLocaleString() : String(v)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Segment Breakdown Table */}
                  {results.segments && Object.keys(results.segments).length > 0 && (
                    <div className="space-y-2">
                      {Object.entries(results.segments).map(([segTitle, rows]: [string, any]) => (
                        <div key={segTitle} className="border rounded-lg overflow-hidden">
                          <div className="bg-muted px-4 py-2 border-b text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            {segTitle.replace(/_/g, ' ')}
                          </div>
                          {Array.isArray(rows) && rows.length > 0 ? (
                            <div className="overflow-x-auto">
                              <table className="w-full text-xs text-left">
                                <thead className="bg-muted/40 border-b">
                                  <tr>
                                    {Object.keys(rows[0]).map((h) => (
                                      <th key={h} className="p-2.5 font-semibold capitalize">
                                        {h.replace(/_/g, ' ')}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {rows.map((row: any, rIdx: number) => (
                                    <tr key={rIdx} className="border-b last:border-0 hover:bg-muted/20">
                                      {Object.values(row).map((val: any, cIdx: number) => (
                                        <td key={cIdx} className="p-2.5 font-medium">
                                          {typeof val === 'number' ? val.toLocaleString() : String(val)}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p className="p-4 text-xs text-muted-foreground">No segment records available.</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Overall KPIs */}
                  {results.kpis && Object.keys(results.kpis).length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">Target Metrics</span>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        {Object.entries(results.kpis).map(([metricName, stats]: [string, any]) => (
                          <div key={metricName} className="p-3 border rounded-lg bg-card">
                            <span className="text-xs text-muted-foreground block truncate">{metricName}</span>
                            <span className="text-base font-bold text-foreground block mt-0.5">
                              {stats?.sum_val !== undefined && stats?.sum_val !== null
                                ? Number(stats.sum_val).toLocaleString(undefined, { maximumFractionDigits: 2 })
                                : 'N/A'}
                            </span>
                            <span className="text-[10px] text-muted-foreground block mt-0.5">
                              Avg: {stats?.avg_val !== undefined && stats?.avg_val !== null ? Number(stats.avg_val).toFixed(2) : '-'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Collapsible Raw Output */}
                  <details className="text-xs text-muted-foreground">
                    <summary className="cursor-pointer font-semibold py-1">View Raw Execution JSON & Provenance</summary>
                    <pre className="bg-muted p-4 rounded text-[11px] font-mono max-h-56 overflow-auto mt-2">
                      {JSON.stringify(results, null, 2)}
                    </pre>
                  </details>
                </CardContent>
              </Card>

            )}
          </div>
        </div>
      )}
    </div>
  )
}
