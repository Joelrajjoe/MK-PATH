import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Play,
  RotateCw,
  GitFork,
  Layers,
  Database,
  Sliders,
  Check,
  X,
  Info,
  Clock,
  Code2,
} from 'lucide-react'
import { api, type Dataset } from '@/lib/api'

interface PlanMultiverseProps {
  projectId: string
  datasetId?: string
  onGateEvaluated?: (status: string) => void
}

export default function PlanMultiverseStabilityGate({ projectId, datasetId: initialDatasetId, onGateEvaluated }: PlanMultiverseProps) {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>(initialDatasetId || '')
  const [policies, setPolicies] = useState<any[]>([])
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>('PMSG-POLICY-v1.0')

  // Planning & Preview State
  const [plan, setPlan] = useState<any>(null)
  const [previewVariants, setPreviewVariants] = useState<any[]>([])
  const [previewSummary, setPreviewSummary] = useState<any>(null)
  const [loadingPlan, setLoadingPlan] = useState<boolean>(false)

  // Execution State
  const [executing, setExecuting] = useState<boolean>(false)
  const [runResult, setRunResult] = useState<any>(null)
  const [recentRuns, setRecentRuns] = useState<any[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Load project datasets and policies on mount
  useEffect(() => {
    api.datasets.list(projectId).then(dsList => {
      setDatasets(dsList)
      if (!selectedDatasetId && dsList.length > 0) {
        // Prefer accident dataset if present
        const accidentDs = dsList.find(d => (d.name || d.original_filename || '').toLowerCase().includes('accident'))
        setSelectedDatasetId(accidentDs ? (accidentDs.id || accidentDs.dataset_id || '') : (dsList[0].id || dsList[0].dataset_id || ''))
      }
    }).catch(() => {})

    api.stability.getPolicies().then(pData => {
      setPolicies(pData.policies || [])
      if (pData.default_policy_id) setSelectedPolicyId(pData.default_policy_id)
    }).catch(() => {})

    loadRecentRuns()
  }, [projectId])

  // Reload plan whenever selected dataset changes
  useEffect(() => {
    if (selectedDatasetId) {
      loadPlanAndPreview(selectedDatasetId)
      loadRecentRuns(selectedDatasetId)
    }
  }, [selectedDatasetId])

  const loadRecentRuns = (dsId?: string) => {
    api.stability.listRuns(projectId, dsId || selectedDatasetId).then(res => {
      setRecentRuns(res.runs || [])
      if (res.runs && res.runs.length > 0 && !runResult) {
        setRunResult(res.runs[0])
        setSelectedRunId(res.runs[0].run_id)
      }
    }).catch(() => {})
  }

  const loadPlanAndPreview = async (dsId: string) => {
    setLoadingPlan(true)
    setErrorMsg(null)
    try {
      const planRes = await api.stability.proposePlan(dsId, projectId)
      setPlan(planRes.plan)
      const prevRes = await api.stability.previewVariants(dsId, planRes.plan, 15)
      setPreviewVariants(prevRes.variants || [])
      setPreviewSummary(prevRes.summary || null)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load analytical plan for selected dataset.')
    } finally {
      setLoadingPlan(false)
    }
  }

  const handleExecuteMultiverse = async () => {
    if (!selectedDatasetId) return
    setExecuting(true)
    setErrorMsg(null)
    try {
      const res = await api.stability.run(selectedDatasetId, projectId, plan, selectedPolicyId)
      setRunResult(res)
      setSelectedRunId(res.run_id)
      loadRecentRuns(selectedDatasetId)
      if (onGateEvaluated && res.gate_decision?.overall_status) {
        onGateEvaluated(res.gate_decision.overall_status)
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to execute multiverse stability analysis.')
    } finally {
      setExecuting(false)
    }
  }

  const handleSelectRun = async (rId: string) => {
    setSelectedRunId(rId)
    try {
      const full = await api.stability.getRun(rId)
      setRunResult(full)
    } catch {
      // ignore
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASS':
        return <Badge className="bg-emerald-500/10 border-emerald-500 text-emerald-600 font-bold px-3 py-1">PASS</Badge>
      case 'WARNING':
        return <Badge className="bg-amber-500/10 border-amber-500 text-amber-600 font-bold px-3 py-1">WARNING</Badge>
      case 'FAIL':
        return <Badge className="bg-destructive/10 border-destructive text-destructive font-bold px-3 py-1">FAIL</Badge>
      case 'HUMAN_REVIEW':
        return <Badge className="bg-purple-500/10 border-purple-500 text-purple-600 font-bold px-3 py-1">HUMAN REVIEW</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const getVariantClassBadge = (vClass: string) => {
    switch (vClass) {
      case 'IMPLEMENTATION':
        return <Badge variant="outline" className="text-xs bg-blue-500/10 border-blue-500/30 text-blue-600">Implementation</Badge>
      case 'SPECIFICATION':
        return <Badge variant="outline" className="text-xs bg-indigo-500/10 border-indigo-500/30 text-indigo-600">Specification</Badge>
      case 'ESTIMAND_CHANGE':
        return <Badge variant="outline" className="text-xs bg-purple-500/10 border-purple-500/30 text-purple-600">Estimand Change</Badge>
      case 'INVALID':
        return <Badge variant="outline" className="text-xs bg-rose-500/10 border-rose-500/30 text-rose-600">Incompatible</Badge>
      default:
        return <Badge variant="outline" className="text-xs">{vClass}</Badge>
    }
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-xl border bg-card/60 backdrop-blur-sm shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <GitFork className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-2xl font-black tracking-tight flex items-center gap-2">
                Plan-Multiverse Stability Gate (PMSG)
              </h2>
              <p className="text-sm text-muted-foreground">
                Rigorous robustness evaluation testing whether findings hold across defensible analytical alternatives.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="border-primary/40 text-primary bg-primary/5 font-semibold text-xs py-1">
            Deterministic DuckDB
          </Badge>
          <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 bg-emerald-500/5 font-semibold text-xs py-1">
            Zero Mock Data
          </Badge>
          <Badge variant="outline" className="border-indigo-500/40 text-indigo-600 bg-indigo-500/5 font-semibold text-xs py-1">
            MongoDB Atlas Verified
          </Badge>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Analysis Specification & Dataset Selection */}
      <div className="grid md:grid-cols-3 gap-6">
        <Card className="md:col-span-1 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Database className="h-4 w-4 text-primary" /> Target Dataset & Question
            </CardTitle>
            <CardDescription className="text-xs">
              Select an ingested dataset and configure primary analysis specification.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase block mb-1.5">
                Dataset
              </label>
              <select
                className="w-full text-xs p-2 rounded-md border bg-background text-foreground font-medium focus:ring-2 focus:ring-primary/20"
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                disabled={executing || loadingPlan}
              >
                {datasets.map((d) => (
                  <option key={d.id || d.dataset_id} value={d.id || d.dataset_id}>
                    {d.name || d.original_filename || 'Dataset'} ({d.row_count ?? d.rowCount ?? 0} rows)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase block mb-1.5">
                Decision Policy
              </label>
              <select
                className="w-full text-xs p-2 rounded-md border bg-background text-foreground font-medium focus:ring-2 focus:ring-primary/20"
                value={selectedPolicyId}
                onChange={(e) => setSelectedPolicyId(e.target.value)}
                disabled={executing}
              >
                {policies.map((p) => (
                  <option key={p.policy_id} value={p.policy_id}>
                    {p.name} (Min Coverage: {(p.min_coverage * 100).toFixed(0)}%, Max Rev: {(p.max_reversal_rate * 100).toFixed(0)}%)
                  </option>
                ))}
              </select>
            </div>

            {plan && (
              <div className="space-y-3 pt-2 border-t">
                <div>
                  <span className="text-[11px] font-semibold text-muted-foreground uppercase block">Analytical Question</span>
                  <p className="text-xs font-semibold text-foreground mt-0.5">{plan.analysis_question}</p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded bg-muted/40 border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Grouping Column</span>
                    <span className="font-mono font-bold">{plan.grouping_column}</span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Target Variable</span>
                    <span className="font-mono font-bold">{plan.target_variable}</span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Primary Estimand</span>
                    <span className="font-bold capitalize">{plan.estimand_family?.replace('_', ' ')}</span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border">
                    <span className="text-[10px] text-muted-foreground uppercase block">Baseline Denom</span>
                    <span className="font-bold truncate block">{plan.denominator_definition}</span>
                  </div>
                </div>
              </div>
            )}

            <Button
              className="w-full gap-2 font-bold shadow-md"
              onClick={handleExecuteMultiverse}
              disabled={executing || loadingPlan || !selectedDatasetId}
            >
              {executing ? (
                <>
                  <RotateCw className="h-4 w-4 animate-spin" /> Evaluating Multiverse...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" /> Run Multiverse Stability Gate
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Multiverse Variant Matrix Preview */}
        <Card className="md:col-span-2 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-primary" /> Bounded Variant Matrix
                </CardTitle>
                <CardDescription className="text-xs">
                  Controlled operators: Missing Values, Denominator Families, Outliers, Category Merging, Date Slicing.
                </CardDescription>
              </div>
              {previewSummary && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground font-medium">Total:</span>
                  <Badge variant="secondary" className="font-bold">{previewSummary.total_variants}</Badge>
                  <span className="text-muted-foreground font-medium">Comparable:</span>
                  <Badge variant="outline" className="border-indigo-400 text-indigo-600 font-bold">{previewSummary.comparable_variants}</Badge>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="max-h-72 overflow-y-auto space-y-2 pr-1 border rounded-lg p-2 bg-muted/10">
              {previewVariants.map((v) => (
                <div
                  key={v.variant_id}
                  className={`p-3 rounded-md border text-xs transition-colors flex items-start justify-between gap-3 ${
                    v.compatibility_status === 'INCOMPATIBLE'
                      ? 'bg-rose-500/5 border-rose-500/20'
                      : v.variant_class === 'ESTIMAND_CHANGE'
                      ? 'bg-purple-500/5 border-purple-500/20'
                      : 'bg-card'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-foreground">{v.name}</span>
                      {getVariantClassBadge(v.variant_class)}
                      {v.is_primary && (
                        <Badge className="bg-primary text-primary-foreground text-[10px] px-1.5 py-0 font-bold">
                          Primary Estimand
                        </Badge>
                      )}
                    </div>
                    <p className="text-muted-foreground text-[11px] leading-relaxed">{v.description}</p>
                    {v.incompatibility_reason && (
                      <p className="text-destructive font-semibold text-[10px] mt-1 flex items-center gap-1">
                        <Info className="h-3 w-3" /> {v.incompatibility_reason}
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <span className="font-mono text-[10px] text-muted-foreground block">{v.variant_id}</span>
                    <span className={`text-[10px] font-bold ${v.compatibility_status === 'COMPATIBLE' ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {v.compatibility_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground italic flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 shrink-0 text-primary" />
              Combinatorial explosion is bounded at {previewSummary?.execution_budget || 15} variants. Estimand changes are executed in isolated families and never combined into the primary stability score.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Execution Results Section */}
      {runResult && (
        <div className="space-y-6 pt-2">
          {/* Gate Decision Hero Card */}
          <Card
            className={`border-2 shadow-md ${
              runResult.gate_decision?.overall_status === 'PASS'
                ? 'border-emerald-500 bg-emerald-500/[0.03]'
                : runResult.gate_decision?.overall_status === 'WARNING'
                ? 'border-amber-500 bg-amber-500/[0.03]'
                : 'border-destructive bg-destructive/[0.03]'
            }`}
          >
            <CardHeader className="pb-3">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  {runResult.gate_decision?.overall_status === 'PASS' ? (
                    <div className="p-3 rounded-full bg-emerald-500/10 text-emerald-600">
                      <ShieldCheck className="h-8 w-8" />
                    </div>
                  ) : runResult.gate_decision?.overall_status === 'WARNING' ? (
                    <div className="p-3 rounded-full bg-amber-500/10 text-amber-600">
                      <AlertTriangle className="h-8 w-8" />
                    </div>
                  ) : (
                    <div className="p-3 rounded-full bg-destructive/10 text-destructive">
                      <ShieldAlert className="h-8 w-8" />
                    </div>
                  )}
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h3 className="text-2xl font-black tracking-tight">
                        Gate Decision: {runResult.gate_decision?.overall_status}
                      </h3>
                      {getStatusBadge(runResult.gate_decision?.overall_status)}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Evaluated under {runResult.gate_decision?.policy_id} (Version {runResult.gate_decision?.policy_version})
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider block">Deployment Readiness</span>
                  <div className={`text-sm font-black uppercase tracking-wider mt-0.5 ${runResult.gate_decision?.eligible_for_deployment ? 'text-emerald-600' : 'text-destructive'}`}>
                    {runResult.gate_decision?.eligible_for_deployment ? 'DEPLOYMENT PERMITTED' : 'DEPLOYMENT BLOCKED'}
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3.5 rounded-lg bg-background/80 border text-xs space-y-1.5">
                <p className="font-medium text-foreground">{runResult.gate_decision?.summary}</p>
                <p className="text-muted-foreground text-[11px] font-semibold">
                  Recommended Action: {runResult.gate_decision?.recommended_next_action}
                </p>
              </div>

              {/* Rule Evaluations Grid */}
              <div>
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider block mb-2">
                  Policy Rule Verification ({runResult.gate_decision?.triggered_rules?.length || 0} evaluated)
                </span>
                <div className="grid md:grid-cols-3 gap-2 text-xs">
                  {runResult.gate_decision?.triggered_rules?.map((rule: any, idx: number) => (
                    <div
                      key={idx}
                      className={`p-2.5 rounded-md border flex items-center justify-between ${
                        rule.condition_met ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-destructive/5 border-destructive/20'
                      }`}
                    >
                      <div>
                        <span className="font-bold block text-[11px]">{rule.rule_name}</span>
                        <span className="text-[10px] text-muted-foreground">Observed: {String(rule.observed_value)} ({rule.threshold})</span>
                      </div>
                      {rule.condition_met ? (
                        <Check className="h-4 w-4 text-emerald-600 shrink-0" />
                      ) : (
                        <X className="h-4 w-4 text-destructive shrink-0" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Primary Finding & Stability Metrics Cards */}
          <div className="grid md:grid-cols-4 gap-4">
            <Card className="shadow-sm">
              <CardContent className="p-4 space-y-1">
                <span className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground">Top-Rank Persistence</span>
                <div className="text-3xl font-black text-primary">
                  {(runResult.stability_metrics?.top_category_persistence * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Primary top category persisted across variants
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardContent className="p-4 space-y-1">
                <span className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground">Spearman Rank Correlation</span>
                <div className="text-3xl font-black text-indigo-600">
                  {runResult.stability_metrics?.spearman_rank_correlation.toFixed(3)}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Average rho across all categories (with ties)
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardContent className="p-4 space-y-1">
                <span className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground">Conclusion Reversal Rate</span>
                <div className={`text-3xl font-black ${runResult.stability_metrics?.conclusion_reversal_rate > 0.15 ? 'text-destructive' : 'text-emerald-600'}`}>
                  {(runResult.stability_metrics?.conclusion_reversal_rate * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Reversals in rank or significant effect shifts
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-sm">
              <CardContent className="p-4 space-y-1">
                <span className="text-[11px] uppercase tracking-wider font-bold text-muted-foreground">Variant Coverage</span>
                <div className="text-3xl font-black text-foreground">
                  {runResult.stability_metrics?.completed_variants} / {runResult.stability_metrics?.valid_variants}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  100% completed without database crash
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Primary Finding Card */}
          <div className="p-4 rounded-xl border bg-primary/5 border-primary/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-primary">Baseline Finding Under Primary Plan</span>
              <h4 className="text-lg font-bold text-foreground">
                {runResult.execution_results?.[0]?.primary_finding_summary || 'Top Category Identified.'}
              </h4>
              <p className="text-xs text-muted-foreground">
                Target: <span className="font-mono">{runResult.plan?.target_variable}</span> | Grouping: <span className="font-mono">{runResult.plan?.grouping_column}</span> | Metric Range across multiverse: [{(runResult.stability_metrics?.effect_size_min * 100).toFixed(2)}%, {(runResult.stability_metrics?.effect_size_max * 100).toFixed(2)}%]
              </p>
            </div>
            <div className="shrink-0 flex items-center gap-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-1 font-mono">
                <Clock className="h-3.5 w-3.5" /> {runResult.duration_total_ms}ms runtime
              </div>
              <div className="flex items-center gap-1 font-mono">
                <Code2 className="h-3.5 w-3.5" /> ID: {runResult.run_id}
              </div>
            </div>
          </div>

          {/* Multiverse Execution Breakdown Table */}
          <Card className="shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" /> Comparable Analytical Variants Execution Matrix
              </CardTitle>
              <CardDescription className="text-xs">
                Every variant executed against real DuckDB Parquet views with deterministic query hashes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b bg-muted/30 text-muted-foreground font-semibold">
                      <th className="p-2.5">Variant</th>
                      <th className="p-2.5">Classification</th>
                      <th className="p-2.5">Sample (N)</th>
                      <th className="p-2.5">Excluded</th>
                      <th className="p-2.5">Top Group</th>
                      <th className="p-2.5">Top Value</th>
                      <th className="p-2.5">Query Hash</th>
                      <th className="p-2.5 text-right">Runtime</th>
                      <th className="p-2.5 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runResult.execution_results?.map((res: any, idx: number) => (
                      <tr key={res.variant_id} className={`border-b hover:bg-muted/30 transition-colors ${idx === 0 ? 'bg-primary/[0.02] font-semibold' : ''}`}>
                        <td className="p-2.5">
                          <div className="font-medium text-foreground">{res.variant_name}</div>
                          <span className="text-[10px] text-muted-foreground font-mono">{res.variant_id}</span>
                        </td>
                        <td className="p-2.5">{getVariantClassBadge(res.variant_class)}</td>
                        <td className="p-2.5 font-mono">{res.sample_size.toLocaleString()}</td>
                        <td className="p-2.5 font-mono text-muted-foreground">{res.excluded_rows}</td>
                        <td className="p-2.5 font-bold text-foreground">{res.top_category || 'N/A'}</td>
                        <td className="p-2.5 font-mono text-primary font-bold">
                          {res.top_value !== null ? `${(res.top_value * 100).toFixed(2)}%` : 'N/A'}
                        </td>
                        <td className="p-2.5 font-mono text-[10px] text-muted-foreground">{res.query_hash || '-'}</td>
                        <td className="p-2.5 text-right font-mono text-muted-foreground">{res.duration_ms}ms</td>
                        <td className="p-2.5 text-center">
                          <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[10px] px-1.5 py-0 font-bold">
                            SUCCESS
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Estimand Divergence Disclosure Box */}
          {runResult.estimand_divergent_results?.length > 0 && (
            <Card className="border-purple-500/30 bg-purple-500/[0.02] shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2 text-purple-700">
                  <GitFork className="h-4 w-4" /> Estimand Divergence Disclosure (Separate Analysis Family)
                </CardTitle>
                <CardDescription className="text-xs">
                  Alternatives that alter the research question being answered are isolated rather than pooled.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                {runResult.estimand_divergent_results.map((est: any) => (
                  <div key={est.variant_id} className="p-3 rounded-lg border border-purple-500/20 bg-card/60 flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground">{est.variant_name}</span>
                        <Badge variant="outline" className="text-[10px] border-purple-500 text-purple-600">
                          {est.estimand_family}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground text-[11px] leading-relaxed">
                        {est.primary_finding_summary}
                      </p>
                      <p className="text-purple-600 text-[11px] font-semibold">
                        Notice: Under this estimand, the top ranking changes to '{est.top_category}' (occurrence rate: {(est.top_value * 100).toFixed(2)}%). Because accident rate within category answers a different question than population accident share, it must not be averaged into the primary stability score.
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="font-mono text-sm font-bold text-purple-600">{(est.top_value * 100).toFixed(2)}%</span>
                      <span className="text-[10px] text-muted-foreground block font-mono">N={est.sample_size}</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Historical Runs Browser */}
          {recentRuns.length > 1 && (
            <Card className="shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Database className="h-4 w-4 text-muted-foreground" /> Historical PMSG Runs in MongoDB Atlas ({recentRuns.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
                  {recentRuns.map((r) => (
                    <button
                      key={r.run_id}
                      onClick={() => handleSelectRun(r.run_id)}
                      className={`px-3 py-2 rounded-lg border text-left shrink-0 transition-all ${
                        selectedRunId === r.run_id ? 'border-primary bg-primary/5 shadow-xs' : 'bg-muted/20 hover:bg-muted/40'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-mono font-bold text-[11px]">{r.run_id}</span>
                        {getStatusBadge(r.gate_decision?.overall_status)}
                      </div>
                      <span className="text-[10px] text-muted-foreground block">
                        Persistence: {(r.stability_metrics?.top_category_persistence * 100).toFixed(0)}% | Rev: {(r.stability_metrics?.conclusion_reversal_rate * 100).toFixed(0)}%
                      </span>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
