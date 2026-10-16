import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertCircle, CheckCircle, ShieldAlert, UserCheck, Activity, ShieldCheck, Loader2, GitFork } from 'lucide-react'
import { api } from '@/lib/api'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import PlanMultiverseStabilityGate from '@/components/verification/PlanMultiverseStabilityGate'
import FaultInjectionBenchmarkConsole from '@/components/verification/FaultInjectionBenchmarkConsole'
import AttestationEvidencePanel from '@/components/attestation/AttestationEvidencePanel'
import LineageExplorer from '@/components/attestation/LineageExplorer'
import AttestationStatusBadge from '@/components/attestation/AttestationStatusBadge'

export default function VerificationCenter() {
  const { projectId } = useParams<{ projectId: string }>()
  const [activeTab, setActiveTab] = useState<'gates' | 'pmsg' | 'benchmark' | 'attestation'>('gates')
  const [selectedGate, setSelectedGate] = useState<string | null>(null)
  const [verificationData, setVerificationData] = useState<any>(null)
  const [envelope, setEnvelope] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [runs, setRuns] = useState<any[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string>('')
  const [selectedDataset, setSelectedDataset] = useState<any>(null)


  const loadVerificationData = async (targetRun?: string) => {
    setLoading(true)
    try {
      // 1. Fetch runs for project
      const runList = await api.runs.list(projectId).catch(() => [])
      setRuns(runList || [])

      const effectiveRunId = targetRun || selectedRunId || (runList && runList.length > 0 ? runList[0].run_id : 'run_1')
      setSelectedRunId(effectiveRunId)

      // 2. Fetch datasets to get real quality score
      const dsList = await api.datasets.list(projectId).catch(() => [])
      const activeDs = dsList && dsList.length > 0 ? dsList[0] : null
      setSelectedDataset(activeDs)
      const qScore = activeDs?.qualityScore ?? activeDs?.profile?.quality_score ?? 100.0

      // 3. Fetch verification gates
      const res = await api.verification.getGates(projectId || 'project_1', effectiveRunId, qScore)
      setVerificationData(res)

      // 4. Fetch attestation envelopes for project
      if (projectId) {
        const envList = await api.attestations.list(projectId).catch(() => [])
        const matched = envList.find((e: any) => e.run_id === effectiveRunId) || (envList.length > 0 ? envList[0] : null)
        setEnvelope(matched)
      }
    } catch (err) {
      console.error('Failed to load verification data:', err)
    } finally {
      setLoading(false)
    }

  }

  useEffect(() => {
    loadVerificationData()
  }, [projectId])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS': return <CheckCircle className="h-5 w-5 text-emerald-500" />
      case 'WARNING': return <AlertCircle className="h-5 w-5 text-orange-500" />
      case 'FAIL': return <ShieldAlert className="h-5 w-5 text-destructive" />
      case 'HUMAN_REVIEW':
      case 'HUMAN REVIEW': return <UserCheck className="h-5 w-5 text-purple-500" />
      default: return <Activity className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getBadgeClass = (status: string) => {
    switch (status) {
      case 'PASS': return 'border-emerald-500 text-emerald-600 bg-emerald-500/10'
      case 'WARNING': return 'border-orange-500 text-orange-600 bg-orange-500/10'
      case 'FAIL': return 'border-destructive text-destructive bg-destructive/10'
      case 'HUMAN_REVIEW':
      case 'HUMAN REVIEW': return 'border-purple-500 text-purple-600 bg-purple-500/10'
      default: return 'border-muted text-muted-foreground'
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const gatesList = verificationData?.gates || verificationData?.summary?.results || []
  const overallState = verificationData?.deployment_status || 'READY'
  const selectedDetails = gatesList.find((g: any) => g.gate_id === selectedGate)
  const failureReason = typeof verificationData?.summary === 'string'
    ? verificationData.summary
    : (verificationData?.summary?.results?.find((g: any) => g.status === 'FAIL')?.reason ||
       'Mandatory verification criteria evaluated.')

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">MK-Path Verification Center</h2>
          <p className="text-muted-foreground text-sm">Evidence-gated trust, robustness, and deployment readiness control.</p>
        </div>

        {/* Dynamic Run & Dataset Selector */}
        <div className="flex items-center gap-3">
          {runs.length > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground font-medium">Run:</span>
              <select
                value={selectedRunId}
                onChange={(e) => {
                  const newRunId = e.target.value
                  setSelectedRunId(newRunId)
                  loadVerificationData(newRunId)
                }}
                className="bg-background border rounded-lg px-2.5 py-1.5 text-xs font-mono font-medium focus:ring-1 focus:ring-primary focus:outline-none"
              >
                {runs.map((r: any) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id.slice(0, 8)} ({r.status})
                  </option>
                ))}
              </select>
            </div>
          )}

          {envelope && (
            <AttestationStatusBadge
              status={envelope.attestation_status}
              keyId={envelope.attestation?.key_id}
            />
          )}

          {selectedDataset && (
            <Badge variant="outline" className="px-2.5 py-1 text-xs font-normal bg-muted/40">
              {selectedDataset.name || selectedDataset.original_filename || 'Dataset'} (QS: {selectedDataset.qualityScore ?? selectedDataset.profile?.quality_score ?? 100})
            </Badge>
          )}
        </div>
      </div>


      <Tabs value={activeTab} onValueChange={(val: any) => setActiveTab(val)} className="space-y-6">
        <TabsList className="bg-muted/60 p-1">
          <TabsTrigger value="gates" className="gap-2 font-semibold text-xs">
            <ShieldCheck className="h-4 w-4" /> Deployment Readiness Gates
          </TabsTrigger>
          <TabsTrigger value="pmsg" className="gap-2 font-semibold text-xs">
            <GitFork className="h-4 w-4" /> Plan-Multiverse Stability Gate (PMSG)
          </TabsTrigger>
          <TabsTrigger value="benchmark" className="gap-2 font-semibold text-xs">
            <ShieldAlert className="h-4 w-4" /> Fault-Injection Benchmark (FIB-VG)
          </TabsTrigger>
          <TabsTrigger value="attestation" className="gap-2 font-semibold text-xs">
            <ShieldCheck className="h-4 w-4 text-indigo-400" /> Attested Result Envelope & Lineage (ARE-HL)
          </TabsTrigger>
        </TabsList>


        <TabsContent value="gates" className="space-y-6 mt-0">
          <div className="grid md:grid-cols-3 gap-6">
            <div className="md:col-span-1 space-y-6">
              <Card className={`border-2 shadow-sm ${overallState === 'BLOCKED' ? 'border-destructive bg-destructive/5' : 'border-emerald-500 bg-emerald-500/5'}`}>
                <CardHeader className="pb-4">
                  <CardTitle className={`flex items-center gap-2 ${overallState === 'BLOCKED' ? 'text-destructive' : 'text-emerald-600'}`}>
                    <ShieldCheck className="h-6 w-6" /> Deployment Readiness
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-black uppercase tracking-widest">{overallState}</div>
                  {overallState === 'BLOCKED' && (
                    <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded text-xs text-destructive font-medium">
                      {failureReason}
                    </div>
                  )}
                  {overallState === 'READY' && (
                    <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded text-xs text-emerald-700 font-medium">
                      All critical verification criteria passed. System is verified for deployment.
                    </div>
                  )}
                </CardContent>
              </Card>

              {selectedDetails && (
                <Card className="shadow-sm">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center justify-between text-base">
                      {selectedDetails.gate_id.replace(/_/g, ' ')}
                      {getStatusIcon(selectedDetails.status)}
                    </CardTitle>
                    <CardDescription className="text-xs">Severity: {selectedDetails.severity}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm">
                    <div>
                      <span className="text-muted-foreground text-xs uppercase block font-semibold">Reason</span>
                      <p className="font-medium text-xs mt-0.5">{selectedDetails.reason || 'Gate evaluated cleanly.'}</p>
                    </div>
                    {selectedDetails.metrics && Object.keys(selectedDetails.metrics).length > 0 && (
                      <div>
                        <span className="text-muted-foreground text-xs uppercase block font-semibold mb-1">Metrics</span>
                        <pre className="bg-muted p-2 rounded text-xs font-mono max-h-36 overflow-auto">
                          {JSON.stringify(selectedDetails.metrics, null, 2)}
                        </pre>
                      </div>
                    )}
                    <div>
                      <span className="text-muted-foreground text-xs uppercase block font-semibold">Recommendation</span>
                      <p className="mt-1 text-xs text-muted-foreground">{selectedDetails.recommendation || 'No action required.'}</p>
                    </div>
                    {selectedDetails.gate_id === 'plan_multiverse_stability' && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full text-xs gap-1.5"
                        onClick={() => setActiveTab('pmsg')}
                      >
                        Open Multiverse Stability Workspace &rarr;
                      </Button>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>

            <div className="md:col-span-2">
              <Card className="shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Mandatory Verification Gates ({gatesList.length})</CardTitle>
                  <CardDescription className="text-xs">
                    Deterministic verification gates required before production release. Click any gate to inspect evidence.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3">
                    {gatesList.map((gate: any) => (
                      <div
                        key={gate.gate_id}
                        className={`flex items-center justify-between p-4 border rounded-lg cursor-pointer transition-colors hover:bg-muted/50 ${selectedGate === gate.gate_id ? 'border-primary shadow-sm bg-primary/5' : ''}`}
                        onClick={() => setSelectedGate(gate.gate_id)}
                      >
                        <div className="flex items-center gap-4">
                          {getStatusIcon(gate.status)}
                          <div>
                            <p className="font-semibold text-sm capitalize">{gate.gate_id.replace(/_/g, ' ')}</p>
                            <p className="text-xs text-muted-foreground">{gate.reason}</p>
                          </div>
                        </div>
                        <Badge variant="outline" className={`w-32 justify-center font-bold text-xs py-1 ${getBadgeClass(gate.status)}`}>
                          {gate.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="pmsg" className="mt-0">
          <PlanMultiverseStabilityGate
            projectId={projectId!}
            onGateEvaluated={() => loadVerificationData()}
          />
        </TabsContent>

        <TabsContent value="benchmark" className="mt-0">
          <FaultInjectionBenchmarkConsole projectId={projectId!} />
        </TabsContent>

        <TabsContent value="attestation" className="mt-0 space-y-6">
          <AttestationEvidencePanel
            envelope={envelope}
            onReverified={(rep) => console.log('Reverified envelope:', rep)}
          />
          <LineageExplorer
            runId={selectedRunId}
            projectId={projectId!}
          />
        </TabsContent>
      </Tabs>

    </div>
  )
}
