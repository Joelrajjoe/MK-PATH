import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  ShieldAlert,
  ShieldCheck,
  Play,
  Download,
  Search,
  CheckCircle2,
  Layers,
  History,
  Info,
  Loader2,
  Lock,
} from 'lucide-react'
import { api } from '@/lib/api'

interface FaultInjectionBenchmarkConsoleProps {
  projectId?: string
}

export default function FaultInjectionBenchmarkConsole({ projectId = 'default' }: FaultInjectionBenchmarkConsoleProps) {
  const [loading, setLoading] = useState<boolean>(true)
  const [running, setRunning] = useState<boolean>(false)
  const [historicalRuns, setHistoricalRuns] = useState<any[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string>('')
  const [currentRun, setCurrentRun] = useState<any>(null)
  const [scenarioResults, setScenarioResults] = useState<any[]>([])

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL')
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'PASS' | 'FAIL' | 'CRITICAL' | 'CLEAN'>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')

  // Detail Modal
  const [inspectScenario, setInspectScenario] = useState<any | null>(null)

  // Load catalog and latest run
  const loadInitialData = async () => {
    setLoading(true)
    try {
      // 1. Fetch run history
      const histData = await api.verificationBenchmark.getHistory(projectId).catch(() => ({ runs: [] }))
      const runs = histData.runs || []
      setHistoricalRuns(runs)

      if (runs.length > 0) {
        const latestRun = runs[0]
        setSelectedRunId(latestRun.run_id)
        setCurrentRun(latestRun)
        setScenarioResults(latestRun.scenario_results || [])
      }
    } catch (err) {
      console.error('Failed to load benchmark data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInitialData()
  }, [projectId])

  // Select a historical run
  const handleSelectRun = async (runId: string) => {
    setSelectedRunId(runId)
    const run = historicalRuns.find((r) => r.run_id === runId)
    if (run) {
      setCurrentRun(run)
      setScenarioResults(run.scenario_results || [])
    } else {
      try {
        const fetched = await api.verificationBenchmark.getRun(runId)
        setCurrentRun(fetched)
        setScenarioResults(fetched.scenario_results || [])
      } catch (err) {
        console.error('Failed to fetch run detail:', err)
      }
    }
  }

  // Trigger a new real-time benchmark execution
  const handleExecuteBenchmark = async (categoryFilter?: string) => {
    setRunning(true)
    try {
      const catParam = categoryFilter && categoryFilter !== 'ALL' ? categoryFilter : undefined
      const newRun = await api.verificationBenchmark.executeRun(projectId, undefined, catParam)
      setCurrentRun(newRun)
      setSelectedRunId(newRun.run_id)
      setScenarioResults(newRun.scenario_results || [])

      // Refresh historical list
      const histData = await api.verificationBenchmark.getHistory(projectId).catch(() => ({ runs: [] }))
      setHistoricalRuns(histData.runs || [])
    } catch (err: any) {
      alert(`Benchmark execution failed: ${err.message}`)
    } finally {
      setRunning(false)
    }
  }

  // Export report as JSON/Markdown
  const handleExportReport = () => {
    if (!currentRun) return
    const blob = new Blob([JSON.stringify(currentRun, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `FIB_VG_REPORT_${currentRun.run_id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Filtered scenario items for explorer
  const filteredScenarios = scenarioResults.filter((s) => {
    if (selectedCategory !== 'ALL' && s.category !== selectedCategory) return false
    if (selectedSeverity !== 'ALL' && s.severity !== selectedSeverity) return false
    if (statusFilter === 'PASS' && s.execution_status !== 'PASS') return false
    if (statusFilter === 'FAIL' && s.execution_status !== 'FAIL') return false
    if (statusFilter === 'CRITICAL' && s.severity !== 'CRITICAL') return false
    if (statusFilter === 'CLEAN' && !s.is_clean_control) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const matchId = s.scenario_id.toLowerCase().includes(q)
      const matchTitle = (s.title || '').toLowerCase().includes(q)
      const matchDesc = (s.fault_description || '').toLowerCase().includes(q)
      if (!matchId && !matchTitle && !matchDesc) return false
    }
    return true
  })

  const metrics = currentRun?.aggregate_metrics
  const gateDecision = currentRun?.gate_decision
  const isApproved = gateDecision?.overall_status === 'RELEASE_APPROVED'

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 bg-card border rounded-lg shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold tracking-tight">Fault-Injection Benchmark for Verification Gates</h2>
            <Badge variant="outline" className="text-xs bg-muted/50 font-mono">
              FIB-VG v1.0
            </Badge>
            {currentRun && (
              <Badge
                className={`text-xs px-2.5 py-0.5 font-bold ${
                  isApproved
                    ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/30'
                    : 'bg-destructive/10 text-destructive border border-destructive/30'
                }`}
              >
                {gateDecision?.overall_status || 'UNKNOWN'}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Empirical validation of detection efficacy, false-block minimization, and deployment containment under controlled mutations.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center flex-wrap gap-2.5">
          {historicalRuns.length > 0 && (
            <div className="flex items-center gap-1.5">
              <History className="h-4 w-4 text-muted-foreground" />
              <select
                value={selectedRunId}
                onChange={(e) => handleSelectRun(e.target.value)}
                className="text-xs font-mono bg-background border rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {historicalRuns.map((r: any) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id} ({r.gate_decision?.overall_status || 'RUN'}) - {new Date(r.started_at).toLocaleTimeString()}
                  </option>
                ))}
              </select>
            </div>
          )}

          <Button
            size="sm"
            onClick={() => handleExecuteBenchmark()}
            disabled={running}
            className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-semibold shadow-sm"
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {running ? 'Executing Real Scenarios...' : 'Run All 42 Scenarios'}
          </Button>

          {currentRun && (
            <Button size="sm" variant="outline" onClick={handleExportReport} className="gap-2 text-xs">
              <Download className="h-4 w-4" /> Export Report
            </Button>
          )}
        </div>
      </div>

      {/* No Runs Empty State */}
      {!currentRun && (
        <Card className="border-dashed p-10 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <ShieldAlert className="h-6 w-6 text-primary" />
          </div>
          <h3 className="mt-4 text-base font-semibold">No Benchmark Executions Recorded</h3>
          <p className="mt-2 text-xs text-muted-foreground max-w-md mx-auto">
            Zero mock or synthetic benchmark results exist. Click "Run All 42 Scenarios" to initiate an isolated, real-time fault-injection evaluation against MK-Path verification gates.
          </p>
          <Button
            size="sm"
            onClick={() => handleExecuteBenchmark()}
            disabled={running}
            className="mt-5 gap-2"
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run All 42 Scenarios
          </Button>
        </Card>
      )}

      {/* Active Run Overview Cards */}
      {currentRun && metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Card 1: Detection Rate */}
          <Card className="shadow-sm border">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardDescription className="text-xs uppercase font-bold text-muted-foreground tracking-wider flex items-center justify-between">
                Detection Rate
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              </CardDescription>
              <CardTitle className="text-2xl font-black text-emerald-600 mt-1">
                {metrics.detection_rate_pct !== null ? `${metrics.detection_rate_pct}%` : 'N/A'}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <p className="text-xs text-muted-foreground font-mono">
                {metrics.detected_faults} / {metrics.eligible_fault_scenarios} faults detected
              </p>
              <div className="w-full bg-muted h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${metrics.detection_rate_pct || 0}%` }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Card 2: False-Block Rate */}
          <Card className="shadow-sm border">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardDescription className="text-xs uppercase font-bold text-muted-foreground tracking-wider flex items-center justify-between">
                False-Block Rate
                <ShieldCheck className="h-4 w-4 text-blue-500" />
              </CardDescription>
              <CardTitle className="text-2xl font-black text-foreground mt-1">
                {metrics.false_block_rate_pct !== null ? `${metrics.false_block_rate_pct}%` : '0.0%'}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <p className="text-xs text-muted-foreground font-mono">
                {metrics.clean_controls_blocked} / {metrics.eligible_clean_controls} clean blocked
              </p>
              <div className="w-full bg-muted h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-destructive h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${metrics.false_block_rate_pct || 0}%` }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Card 3: Critical Escapes */}
          <Card className={`shadow-sm border ${metrics.critical_faults_passed > 0 ? 'border-destructive bg-destructive/5' : ''}`}>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardDescription className="text-xs uppercase font-bold text-muted-foreground tracking-wider flex items-center justify-between">
                Critical Escapes
                <ShieldAlert className={`h-4 w-4 ${metrics.critical_faults_passed > 0 ? 'text-destructive' : 'text-emerald-500'}`} />
              </CardDescription>
              <CardTitle className={`text-2xl font-black mt-1 ${metrics.critical_faults_passed > 0 ? 'text-destructive' : 'text-emerald-600'}`}>
                {metrics.critical_faults_passed}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <p className="text-xs text-muted-foreground font-mono">
                {metrics.critical_faults_passed} / {metrics.eligible_critical_faults} critical passed
              </p>
              <span className="text-[11px] font-medium text-muted-foreground mt-1 block">
                Target: 0 Escapes (Strict Policy)
              </span>
            </CardContent>
          </Card>

          {/* Card 4: Deployment Containment */}
          <Card className="shadow-sm border">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardDescription className="text-xs uppercase font-bold text-muted-foreground tracking-wider flex items-center justify-between">
                Deployment Containment
                <Lock className="h-4 w-4 text-purple-500" />
              </CardDescription>
              <CardTitle className="text-2xl font-black text-purple-600 mt-1">
                {metrics.deployment_blocking_rate_pct !== null ? `${metrics.deployment_blocking_rate_pct}%` : 'N/A'}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 pt-0">
              <p className="text-xs text-muted-foreground font-mono">
                {metrics.correctly_blocked_deployments} / {metrics.eligible_critical_blocked_scenarios} blocked
              </p>
              <div className="w-full bg-muted h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-purple-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${metrics.deployment_blocking_rate_pct || 0}%` }}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Release Decision & Secondary Metrics Bar */}
      {currentRun && gateDecision && (
        <Card className="border shadow-sm p-4 bg-muted/20">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Release Evaluation:</span>
                <span className="text-xs font-semibold">{gateDecision.summary}</span>
              </div>
              {gateDecision.violations && gateDecision.violations.length > 0 && (
                <ul className="mt-2 text-xs text-destructive list-disc list-inside space-y-1">
                  {gateDecision.violations.map((v: string, i: number) => (
                    <li key={i}>{v}</li>
                  ))}
                </ul>
              )}
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground self-end md:self-center">
              <span>Diagnosis: <strong>{metrics.diagnosis_accuracy_pct}%</strong></span>
              <span>Audit: <strong>{metrics.audit_completeness_pct}%</strong></span>
              <span>Coverage: <strong>{metrics.completed_scenarios} / {metrics.total_registered_scenarios}</strong></span>
              <Badge variant="outline" className="text-[10px] bg-background">Atlas Confirmed</Badge>
            </div>
          </div>
        </Card>
      )}

      {/* Scenario Explorer */}
      {currentRun && (
        <Card className="border shadow-sm">
          <CardHeader className="pb-3 border-b">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Layers className="h-4 w-4" /> Scenario Execution Explorer
                </CardTitle>
                <CardDescription className="text-xs">
                  Inspect independent oracle expectations versus real system observations across all {scenarioResults.length} scenarios.
                </CardDescription>
              </div>

              {/* Search & Filter Controls */}
              <div className="flex items-center flex-wrap gap-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search scenarios..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="text-xs bg-background border rounded pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary w-44"
                  />
                </div>

                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="text-xs bg-background border rounded px-2.5 py-1.5 focus:outline-none"
                >
                  <option value="ALL">All Categories</option>
                  <option value="DATA_INTEGRITY">Data Integrity</option>
                  <option value="ANALYTICAL_CORRECTNESS">Analytical Correctness</option>
                  <option value="SEMANTIC_GOVERNANCE">Semantic & Governance</option>
                  <option value="AGENT_ORCHESTRATION">Agent Orchestration</option>
                  <option value="VERIFICATION_GATE_BYPASS">Gate Bypass</option>
                  <option value="STORAGE_PERSISTENCE">Storage & Persistence</option>
                  <option value="FRONTEND_API_INTEGRITY">API & Frontend</option>
                  <option value="AUDIT_EVIDENCE">Audit & Evidence</option>
                </select>

                <select
                  value={selectedSeverity}
                  onChange={(e) => setSelectedSeverity(e.target.value)}
                  className="text-xs bg-background border rounded px-2.5 py-1.5 focus:outline-none"
                >
                  <option value="ALL">All Severities</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>

                <div className="flex items-center border rounded bg-background p-0.5 text-xs">
                  <button
                    onClick={() => setStatusFilter('ALL')}
                    className={`px-2 py-1 rounded text-[11px] font-medium ${statusFilter === 'ALL' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground'}`}
                  >
                    All ({scenarioResults.length})
                  </button>
                  <button
                    onClick={() => setStatusFilter('FAIL')}
                    className={`px-2 py-1 rounded text-[11px] font-medium ${statusFilter === 'FAIL' ? 'bg-destructive text-destructive-foreground' : 'text-muted-foreground'}`}
                  >
                    Failed ({scenarioResults.filter(s => s.execution_status === 'FAIL').length})
                  </button>
                  <button
                    onClick={() => setStatusFilter('CLEAN')}
                    className={`px-2 py-1 rounded text-[11px] font-medium ${statusFilter === 'CLEAN' ? 'bg-blue-600 text-white' : 'text-muted-foreground'}`}
                  >
                    Controls ({scenarioResults.filter(s => s.is_clean_control).length})
                  </button>
                </div>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0 overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/40 border-b text-[11px] text-muted-foreground uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Scenario</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Expected vs Observed</th>
                  <th className="py-2.5 px-3">Gate Decision</th>
                  <th className="py-2.5 px-3">Deployment</th>
                  <th className="py-2.5 px-3">Result</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredScenarios.map((sc: any) => {
                  const isPass = sc.execution_status === 'PASS'
                  return (
                    <tr key={sc.scenario_id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-2.5 px-3 font-mono font-bold text-foreground">
                        <div className="flex items-center gap-1.5">
                          {sc.is_clean_control ? (
                            <Badge variant="outline" className="text-[10px] bg-blue-500/10 text-blue-600 border-blue-500/30">
                              CONTROL
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px] bg-purple-500/10 text-purple-600 border-purple-500/30">
                              MUTATION
                            </Badge>
                          )}
                          <span>{sc.scenario_id}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground font-sans font-normal truncate max-w-xs mt-0.5">
                          {sc.title}
                        </div>
                      </td>

                      <td className="py-2.5 px-3 font-mono text-[11px] text-muted-foreground">
                        {sc.category}
                      </td>

                      <td className="py-2.5 px-3">
                        <Badge
                          variant="outline"
                          className={`text-[10px] font-bold ${
                            sc.severity === 'CRITICAL'
                              ? 'border-destructive/40 text-destructive bg-destructive/10'
                              : sc.severity === 'HIGH'
                              ? 'border-orange-500/40 text-orange-600 bg-orange-500/10'
                              : 'border-muted text-muted-foreground'
                          }`}
                        >
                          {sc.severity}
                        </Badge>
                      </td>

                      <td className="py-2.5 px-3 font-mono text-[11px]">
                        <span className="text-muted-foreground">Exp:</span> {sc.expected_detection ? 'DETECT' : 'PASS'}{' '}
                        <span className="text-muted-foreground">| Obs:</span>{' '}
                        <span className={sc.observed_detection === sc.expected_detection ? 'text-emerald-600 font-semibold' : 'text-destructive font-semibold'}>
                          {sc.observed_detection ? 'DETECT' : 'PASS'}
                        </span>
                      </td>

                      <td className="py-2.5 px-3">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            sc.observed_gate_decision === 'PASS'
                              ? 'border-emerald-500/30 text-emerald-600 bg-emerald-500/10'
                              : sc.observed_gate_decision === 'WARNING'
                              ? 'border-orange-500/30 text-orange-600 bg-orange-500/10'
                              : 'border-destructive/30 text-destructive bg-destructive/10'
                          }`}
                        >
                          {sc.observed_gate_decision}
                        </Badge>
                      </td>

                      <td className="py-2.5 px-3 font-mono text-[11px]">
                        {sc.observed_deployment_blocked ? (
                          <span className="text-destructive font-semibold flex items-center gap-1">
                            <Lock className="h-3 w-3" /> BLOCKED
                          </span>
                        ) : (
                          <span className="text-emerald-600 font-semibold flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" /> READY
                          </span>
                        )}
                      </td>

                      <td className="py-2.5 px-3">
                        <Badge
                          className={`text-[10px] font-bold ${
                            isPass
                              ? 'bg-emerald-500 text-white'
                              : 'bg-destructive text-destructive-foreground'
                          }`}
                        >
                          {sc.execution_status}
                        </Badge>
                      </td>

                      <td className="py-2.5 px-3 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setInspectScenario(sc)}
                          className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                        >
                          <Info className="h-3.5 w-3.5" />
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Inspect Scenario Modal Drawer */}
      {inspectScenario && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <Card className="w-full max-w-2xl border shadow-xl bg-card">
            <CardHeader className="border-b pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-mono">{inspectScenario.scenario_id}</Badge>
                    <Badge>{inspectScenario.category}</Badge>
                    <Badge variant="outline" className="border-destructive/40 text-destructive">{inspectScenario.severity}</Badge>
                  </div>
                  <CardTitle className="text-base font-bold mt-2">{inspectScenario.title}</CardTitle>
                </div>
                <Button size="sm" variant="ghost" onClick={() => setInspectScenario(null)}>
                  ✕
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4 text-xs">
              <div>
                <span className="font-bold text-muted-foreground uppercase tracking-wider block text-[10px]">Description:</span>
                <p className="mt-1 text-foreground leading-relaxed">{inspectScenario.fault_description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 p-3 bg-muted/30 rounded border">
                <div>
                  <span className="font-bold text-muted-foreground uppercase tracking-wider block text-[10px]">Independent Expected Outcome:</span>
                  <ul className="mt-1 space-y-1 font-mono text-[11px]">
                    <li>Detection: <strong>{inspectScenario.expected_detection ? 'TRUE' : 'FALSE'}</strong></li>
                    <li>Gate Decision: <strong>{inspectScenario.expected_gate_decision}</strong></li>
                    <li>Deployment Blocked: <strong>{inspectScenario.expected_deployment_blocked ? 'TRUE' : 'FALSE'}</strong></li>
                    <li>Diagnosis Category: <strong>{inspectScenario.expected_diagnosis_category}</strong></li>
                  </ul>
                </div>

                <div>
                  <span className="font-bold text-muted-foreground uppercase tracking-wider block text-[10px]">Real System Observation:</span>
                  <ul className="mt-1 space-y-1 font-mono text-[11px]">
                    <li>Observed Detection: <strong>{inspectScenario.observed_detection ? 'TRUE' : 'FALSE'}</strong></li>
                    <li>Observed Gate: <strong>{inspectScenario.observed_gate_decision}</strong></li>
                    <li>Deployment Blocked: <strong>{inspectScenario.observed_deployment_blocked ? 'TRUE' : 'FALSE'}</strong></li>
                    <li>Diagnosis: <strong>{inspectScenario.observed_diagnosis || 'NONE'}</strong></li>
                  </ul>
                </div>
              </div>

              <div>
                <span className="font-bold text-muted-foreground uppercase tracking-wider block text-[10px]">Audit Evidence References:</span>
                <div className="mt-1 p-2 bg-background border rounded font-mono text-[11px] space-y-1 text-muted-foreground">
                  {inspectScenario.evidence_references && inspectScenario.evidence_references.length > 0 ? (
                    inspectScenario.evidence_references.map((ev: string, idx: number) => (
                      <div key={idx}>• {ev}</div>
                    ))
                  ) : (
                    <div>No evidence recorded</div>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-2 border-t">
                <span>Duration: {inspectScenario.duration_ms} ms</span>
                <span>Cleanup: {inspectScenario.cleanup_verified ? 'Verified Safe' : 'Unconfirmed'}</span>
                <span>Timestamp: {new Date(inspectScenario.timestamp).toLocaleString()}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
