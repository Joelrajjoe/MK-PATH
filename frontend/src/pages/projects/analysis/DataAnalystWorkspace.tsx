import { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  CheckCircle,
  BrainCircuit,
  BarChart,
  Loader2,
  TrendingUp,
  Users,
  Sparkles,
  Database,
  ShieldCheck,
  Activity,
  DollarSign
} from 'lucide-react'
import { api } from '@/lib/api'

interface AnalysisTemplate {
  id: string
  title: string
  description: string
  query: string
  badge: string
  tags: string[]
  icon: any
}

const TEMPLATES: AnalysisTemplate[] = [
  {
    id: 'sales_margin',
    title: 'Executive Sales & Profit Margin Performance',
    description: 'Deep-dive into sales totals, profit distributions, and regional performance margins across product categories.',
    query: 'Analyze sales performance, profit margins, and revenue breakdown by region and category',
    badge: 'Executive & Revenue',
    tags: ['Sales', 'Profit', 'Region', 'Category'],
    icon: TrendingUp,
  },
  {
    id: 'customer_segments',
    title: 'Customer Segments & Operational Efficiency',
    description: 'Evaluate customer segment profitability, discount exposure, and order quantities to optimize delivery operations.',
    query: 'Analyze customer segments, order volume, discounting trends, and operational efficiency across Consumer, Corporate, and Home Office',
    badge: 'Operations & Churn',
    tags: ['Segment', 'Discount', 'Quantity', 'Ship Mode'],
    icon: Users,
  },
]

export default function DataAnalystWorkspace() {
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialDatasetId = searchParams.get('datasetId')

  const [query, setQuery] = useState('')
  const [datasets, setDatasets] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [plan, setPlan] = useState<any>(null)
  const [executing, setExecuting] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTemplate, setActiveTemplate] = useState<string | null>(null)

  useEffect(() => {
    if (projectId) {
      api.datasets.list(projectId).then((ds: any[]) => {
        setDatasets(ds)
        if (ds.length > 0) {
          // If a datasetId was passed in URL params, prioritize it
          if (initialDatasetId && ds.some(d => (d.dataset_id || d.id) === initialDatasetId)) {
            setSelectedDatasetId(initialDatasetId)
          } else {
            // Otherwise, prioritize derived/preprocessed dataset if one exists
            const derivedDs = ds.find(d => d.is_derived === true || (d.name && d.name.toLowerCase().includes('preprocessed')))
            if (derivedDs) {
              const dId = derivedDs.dataset_id || derivedDs.id
              setSelectedDatasetId(dId)
              setSearchParams({ datasetId: dId })
            } else {
              setSelectedDatasetId(ds[0].dataset_id || ds[0].id)
            }
          }
        }
      })
    }
  }, [projectId, initialDatasetId])

  const selectedDataset = datasets.find(d => (d.dataset_id || d.id) === selectedDatasetId)
  const isPreprocessed = selectedDataset?.is_derived === true || selectedDataset?.name?.toLowerCase().includes('preprocessed')
  const derivedDatasetAvailable = datasets.find(d => d.is_derived === true || d.name?.toLowerCase().includes('preprocessed'))

  const handleSelectDataset = (id: string) => {
    setSelectedDatasetId(id)
    setSearchParams({ datasetId: id })
    setPlan(null)
    setResults(null)
    setError(null)
  }

  const handleGeneratePlan = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
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

  const handleRunTemplate = async (tmpl: AnalysisTemplate) => {
    if (!selectedDatasetId) return
    setActiveTemplate(tmpl.id)
    setQuery(tmpl.query)
    setGenerating(true)
    setExecuting(true)
    setError(null)
    setPlan(null)
    setResults(null)
    try {
      const planRes = await api.analysis.plan(selectedDatasetId, tmpl.query)
      setPlan(planRes.plan)
      const execRes = await api.analysis.execute(selectedDatasetId, planRes.plan)
      setResults(execRes.results)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Failed to execute template dashboard.')
    } finally {
      setGenerating(false)
      setExecuting(false)
    }
  }

  const formatMetricVal = (key: string, val: any) => {
    if (val === null || val === undefined) return 'N/A'
    const num = Number(val)
    if (isNaN(num)) return String(val)
    const isCurrency = key.toLowerCase().includes('sales') || key.toLowerCase().includes('profit') || key.toLowerCase().includes('revenue')
    if (isCurrency) {
      return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
    if (key.toLowerCase().includes('discount')) {
      return `${(num * 100).toFixed(1)}%`
    }
    return num.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Data Analyst Workspace & Dashboards</h2>
          <p className="text-muted-foreground">
            Execute deterministic analytical plans via DuckDB on your preprocessed datasets.
          </p>
        </div>
      </div>

      {/* Dataset Provenance Status Banner */}
      {isPreprocessed ? (
        <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-medium">
            <ShieldCheck className="h-5 w-5 text-emerald-600 shrink-0" />
            <div>
              <span className="font-bold">Active Dataset: Preprocessed Parquet</span>
              <span className="text-muted-foreground block text-[11px]">
                Features winsorized via IQR, text normalized, constant columns removed, nulls imputed. Real computations will run on clean data.
              </span>
            </div>
          </div>
          <span className="font-mono bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 px-2.5 py-1 rounded text-[11px] shrink-0 font-semibold">
            {selectedDataset?.name || selectedDatasetId}
          </span>
        </div>
      ) : derivedDatasetAvailable ? (
        <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
            <Database className="h-5 w-5 text-amber-600 shrink-0" />
            <span>
              <strong>Notice:</strong> Currently viewing raw dataset. A preprocessed dataset is available.
            </span>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="border-amber-500/40 text-amber-700 dark:text-amber-400 hover:bg-amber-500/10 h-7 text-xs"
            onClick={() => handleSelectDataset(derivedDatasetAvailable.dataset_id || derivedDatasetAvailable.id)}
          >
            Switch to Preprocessed Dataset
          </Button>
        </div>
      ) : null}

      {/* Sample Templates Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground">
              Sample Analytical Dashboard Templates
            </h3>
          </div>
          <span className="text-xs text-muted-foreground">1-Click Execution on Preprocessed Data</span>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {TEMPLATES.map((tmpl) => {
            const Icon = tmpl.icon
            const isRunning = (generating || executing) && activeTemplate === tmpl.id
            return (
              <Card
                key={tmpl.id}
                className={`relative overflow-hidden transition-all border hover:border-primary/50 ${
                  activeTemplate === tmpl.id && results ? 'border-primary ring-1 ring-primary/30 shadow-md' : ''
                }`}
              >
                <div className="p-5 flex flex-col justify-between h-full space-y-4">
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                          <Icon className="h-5 w-5" />
                        </div>
                        <h4 className="font-bold text-sm leading-tight text-foreground">{tmpl.title}</h4>
                      </div>
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-muted text-muted-foreground">
                        {tmpl.badge}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {tmpl.description}
                    </p>
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {tmpl.tags.map(t => (
                        <span key={t} className="text-[10px] font-mono bg-muted/60 text-muted-foreground px-2 py-0.5 rounded">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t flex items-center justify-between gap-2">
                    <span className="text-[11px] text-muted-foreground italic truncate max-w-[220px]">
                      "{tmpl.query}"
                    </span>
                    <Button
                      size="sm"
                      disabled={generating || executing || !selectedDatasetId}
                      className="bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold shrink-0"
                      onClick={() => handleRunTemplate(tmpl)}
                    >
                      {isRunning ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                          Running...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                          Generate Dashboard
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Query Bar */}
      <Card>
        <CardContent className="p-5">
          <form onSubmit={handleGeneratePlan} className="space-y-3">
            {datasets.length > 0 && (
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-xs font-semibold text-muted-foreground uppercase">Dataset:</span>
                <select
                  className="border rounded px-3 py-1 text-sm bg-background font-medium max-w-md truncate"
                  value={selectedDatasetId}
                  onChange={(e) => handleSelectDataset(e.target.value)}
                >
                  {datasets.map(d => (
                    <option key={d.id || d.dataset_id} value={d.id || d.dataset_id}>
                      {d.is_derived ? '✨ [Preprocessed] ' : ''}{d.name || d.original_filename} ({((d.id || d.dataset_id) as string).slice(0, 8)}...)
                    </option>
                  ))}
                </select>
                {isPreprocessed && (
                  <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    Preprocessed View
                  </span>
                )}
              </div>
            )}
            <div className="flex gap-3">
              <Input
                placeholder="Or type custom prompt: e.g. Analyze sales and profit margins by region and category"
                value={query}
                onChange={e => {
                  setQuery(e.target.value)
                  setActiveTemplate(null)
                }}
                className="text-sm py-5"
              />
              <Button type="submit" size="default" className="px-6 shrink-0" disabled={generating || executing || !selectedDatasetId}>
                {generating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <BrainCircuit className="h-4 w-4 mr-2" />}
                Analyze
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-red-500/50 bg-red-500/5 p-4 text-red-600 font-medium text-sm">
          {error}
        </Card>
      )}

      {/* Plan and Results Area */}
      {plan && (
        <div className="grid md:grid-cols-3 gap-6">
          {/* Analytical Plan Card */}
          <div className="md:col-span-1 space-y-6">
            <Card className="border-primary/30">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <BarChart className="h-4 w-4 text-primary" /> Analytical Plan
                </CardTitle>
                <CardDescription>Generated for query execution</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div>
                  <span className="font-semibold text-muted-foreground block uppercase text-[10px]">Objective</span>
                  <p className="font-medium text-foreground mt-0.5">{plan.objective || query}</p>
                </div>
                <div>
                  <span className="font-semibold text-muted-foreground block uppercase text-[10px]">Target Metrics</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {plan.metrics && plan.metrics.length > 0 ? (
                      plan.metrics.map((m: string) => (
                        <span key={m} className="bg-primary/10 text-primary font-mono px-2 py-0.5 rounded text-[11px] font-semibold">
                          {m}
                        </span>
                      ))
                    ) : (
                      <span className="text-muted-foreground font-mono">None</span>
                    )}
                  </div>
                </div>
                <div>
                  <span className="font-semibold text-muted-foreground block uppercase text-[10px]">Dimensions</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {plan.dimensions && plan.dimensions.length > 0 ? (
                      plan.dimensions.map((d: string) => (
                        <span key={d} className="bg-muted text-foreground font-mono px-2 py-0.5 rounded text-[11px]">
                          {d}
                        </span>
                      ))
                    ) : (
                      <span className="text-muted-foreground font-mono">None</span>
                    )}
                  </div>
                </div>
                {plan.filters && plan.filters.length > 0 && (
                  <div>
                    <span className="font-semibold text-muted-foreground block uppercase text-[10px]">Filters</span>
                    <div className="space-y-1 mt-1">
                      {plan.filters.map((f: any, idx: number) => (
                        <div key={idx} className="bg-muted/60 p-1.5 rounded text-[11px] font-mono">
                          {f.column} = "{f.value}"
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
              <CardFooter className="pt-2">
                <Button className="w-full text-xs" onClick={handleExecutePlan} disabled={executing}>
                  {executing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle className="h-4 w-4 mr-2" />}
                  Execute Analysis Plan
                </Button>
              </CardFooter>
            </Card>
          </div>

          {/* Results & Dashboard View */}
          <div className="md:col-span-2 space-y-6">
            {!results ? (
              <div className="h-full min-h-[300px] flex flex-col items-center justify-center border border-dashed rounded-lg text-muted-foreground p-8 text-center space-y-3">
                <BrainCircuit className="h-10 w-10 text-muted-foreground/40" />
                <p className="text-sm">Plan generated. Click "Execute Analysis Plan" to compute metrics via DuckDB.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Executive Summary */}
                <Card className="border-primary/20 bg-primary/5">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xs uppercase font-bold tracking-wider text-primary flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5" /> Executive Summary & Insights
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm font-medium text-foreground leading-relaxed">
                      {results.summary || results.executive_summary || 'Analysis executed successfully.'}
                    </p>
                  </CardContent>
                </Card>

                {/* Target Metric KPI Cards */}
                {results.kpis && Object.keys(results.kpis).length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                      Target Metric KPIs (Preprocessed Dataset)
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {Object.entries(results.kpis).map(([metricName, stats]: [string, any]) => {
                        const isRev = metricName.toLowerCase().includes('sales') || metricName.toLowerCase().includes('profit')
                        return (
                          <Card key={metricName} className="p-3.5 bg-card border shadow-sm">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-muted-foreground truncate">{metricName}</span>
                              {isRev ? (
                                <DollarSign className="h-3.5 w-3.5 text-emerald-600" />
                              ) : (
                                <Activity className="h-3.5 w-3.5 text-primary" />
                              )}
                            </div>
                            <span className="text-lg font-bold text-foreground block mt-1">
                              {formatMetricVal(metricName, stats?.sum_val)}
                            </span>
                            <div className="mt-1 pt-1 border-t text-[10px] text-muted-foreground space-y-0.5">
                              <div>Avg: <span className="font-semibold text-foreground">{formatMetricVal(metricName, stats?.avg_val)}</span></div>
                              {stats?.max_val !== undefined && (
                                <div>Max: <span className="font-semibold text-foreground">{formatMetricVal(metricName, stats?.max_val)}</span></div>
                              )}
                            </div>
                          </Card>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Segment Breakdown Tables with Visual Distribution */}
                {results.segments && Object.keys(results.segments).length > 0 && (
                  <div className="space-y-4">
                    {Object.entries(results.segments).map(([segTitle, rows]: [string, any]) => {
                      if (!Array.isArray(rows) || rows.length === 0) return null
                      const firstRow = rows[0]
                      const numericKeys = Object.keys(firstRow).filter(k => typeof firstRow[k] === 'number')
                      const primaryNumKey = numericKeys.find(k => k.toLowerCase().includes('sum') || k.toLowerCase().includes('sales') || k.toLowerCase().includes('profit')) || numericKeys[0]
                      const maxVal = primaryNumKey ? Math.max(...rows.map((r: any) => Number(r[primaryNumKey]) || 0), 1) : 1
                      const dimKey = Object.keys(firstRow).find(k => typeof firstRow[k] === 'string') || Object.keys(firstRow)[0]

                      return (
                        <Card key={segTitle} className="overflow-hidden">
                          <CardHeader className="bg-muted/30 py-3 border-b flex flex-row items-center justify-between">
                            <div>
                              <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                Distribution Breakdown: {segTitle.replace(/_/g, ' ')}
                              </CardTitle>
                              <CardDescription className="text-[11px]">
                                Real-time group aggregation computed from preprocessed Parquet table
                              </CardDescription>
                            </div>
                            <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded text-muted-foreground font-semibold">
                              {rows.length} segments
                            </span>
                          </CardHeader>
                          <CardContent className="p-0">
                            {/* Visual Proportional Bars for Top Dimension */}
                            {primaryNumKey && rows.length <= 10 && (
                              <div className="p-4 border-b bg-background/50 space-y-2">
                                <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground block">
                                  Proportional Volume ({primaryNumKey.replace(/_/g, ' ')})
                                </span>
                                <div className="space-y-1.5">
                                  {rows.map((row: any, rIdx: number) => {
                                    const val = Number(row[primaryNumKey]) || 0
                                    const pct = Math.min(Math.max((val / maxVal) * 100, 2), 100)
                                    return (
                                      <div key={rIdx} className="space-y-0.5">
                                        <div className="flex justify-between text-xs">
                                          <span className="font-semibold text-foreground">{String(row[dimKey])}</span>
                                          <span className="font-mono text-muted-foreground">{formatMetricVal(primaryNumKey, val)}</span>
                                        </div>
                                        <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                                          <div
                                            className="bg-primary h-2 rounded-full transition-all duration-500"
                                            style={{ width: `${pct}%` }}
                                          />
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Full Table */}
                            <div className="overflow-x-auto">
                              <table className="w-full text-xs text-left">
                                <thead className="bg-muted/40 border-b">
                                  <tr>
                                    {Object.keys(firstRow).map((h) => (
                                      <th key={h} className="p-2.5 font-semibold capitalize text-muted-foreground">
                                        {h.replace(/_/g, ' ')}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {rows.map((row: any, rIdx: number) => (
                                    <tr key={rIdx} className="border-b last:border-0 hover:bg-muted/20 transition-colors">
                                      {Object.entries(row).map(([colKey, val]: [string, any], cIdx: number) => (
                                        <td key={cIdx} className="p-2.5 font-medium">
                                          {typeof val === 'number'
                                            ? formatMetricVal(colKey, val)
                                            : String(val)}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </CardContent>
                        </Card>
                      )
                    })}
                  </div>
                )}

                {/* Filtered Findings */}
                {results.filtered_results && results.filtered_results.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">
                      Filtered Targeted Insights
                    </span>
                    <div className="grid sm:grid-cols-2 gap-3">
                      {results.filtered_results.map((fr: any, idx: number) => (
                        <Card key={idx} className="p-3.5 bg-emerald-500/5 border-emerald-500/20">
                          <span className="text-xs font-bold text-emerald-600 block">{fr.filter}</span>
                          <div className="mt-2 space-y-1">
                            {Object.entries(fr.results || {}).map(([k, v]: [string, any]) => (
                              <div key={k} className="flex justify-between text-xs">
                                <span className="capitalize text-muted-foreground">{k.replace(/_/g, ' ')}:</span>
                                <span className="font-semibold font-mono">{formatMetricVal(k, v)}</span>
                              </div>
                            ))}
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {/* DuckDB SQL Provenance Accordion */}
                <details className="text-xs text-muted-foreground border rounded-lg p-3 bg-muted/20">
                  <summary className="cursor-pointer font-semibold py-0.5 text-foreground flex items-center justify-between">
                    <span>Audit & Provenance: DuckDB SQL Query Log ({results.provenance?.length || 0})</span>
                    <span className="text-[11px] text-muted-foreground">Deterministic Execution</span>
                  </summary>
                  <div className="mt-3 space-y-2">
                    {results.provenance && results.provenance.length > 0 ? (
                      results.provenance.map((p: any, idx: number) => (
                        <div key={idx} className="bg-background border rounded p-2 text-[11px] font-mono space-y-1">
                          <div className="flex justify-between text-muted-foreground text-[10px]">
                            <span>Table: {p.table}</span>
                            <span>{p.timestamp ? new Date(p.timestamp).toLocaleTimeString() : ''}</span>
                          </div>
                          <div className="text-primary font-semibold break-all">{p.query}</div>
                        </div>
                      ))
                    ) : (
                      <pre className="bg-background p-2 rounded text-[10px] font-mono overflow-auto">
                        {JSON.stringify(results, null, 2)}
                      </pre>
                    )}
                  </div>
                </details>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
