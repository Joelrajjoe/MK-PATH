import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle, ShieldAlert, UserCheck, Activity, ShieldCheck, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

export default function VerificationCenter() {
  const { projectId } = useParams<{ projectId: string }>()
  const [selectedGate, setSelectedGate] = useState<string | null>(null)
  const [verificationData, setVerificationData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.verification.getGates(projectId || 'project_1', 'run_1')
      .then(res => setVerificationData(res))
      .catch(() => {})
      .finally(() => setLoading(false))
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

  const gatesList = verificationData?.gates || []
  const overallState = verificationData?.deployment_status || 'READY'
  const selectedDetails = gatesList.find((g: any) => g.gate_id === selectedGate)

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">MK-Path Verification Center</h2>
        <p className="text-muted-foreground">Central evidence-gated trust and control interface for deployment readiness.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-1 space-y-6">
          <Card className={`border-2 ${overallState === 'BLOCKED' ? 'border-destructive bg-destructive/5' : 'border-emerald-500 bg-emerald-500/5'}`}>
            <CardHeader className="pb-4">
              <CardTitle className={`flex items-center gap-2 ${overallState === 'BLOCKED' ? 'text-destructive' : 'text-emerald-600'}`}>
                <ShieldCheck className="h-6 w-6" /> Deployment Readiness
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-black uppercase tracking-widest">{overallState}</div>
              {overallState === 'BLOCKED' && (
                <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded text-xs text-destructive font-medium">
                  {verificationData?.summary || 'Mandatory verification gates failed.'}
                </div>
              )}
            </CardContent>
          </Card>

          {selectedDetails && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-base">
                  {selectedDetails.gate_id}
                  {getStatusIcon(selectedDetails.status)}
                </CardTitle>
                <CardDescription>Severity: {selectedDetails.severity}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <span className="text-muted-foreground text-xs uppercase block font-semibold">Reason</span>
                  <p className="font-medium">{selectedDetails.reason || 'Gate evaluated cleanly.'}</p>
                </div>
                {selectedDetails.metrics && (
                  <div>
                    <span className="text-muted-foreground text-xs uppercase block font-semibold mb-1">Metrics</span>
                    <pre className="bg-muted p-2 rounded text-xs font-mono max-h-32 overflow-auto">
                      {JSON.stringify(selectedDetails.metrics, null, 2)}
                    </pre>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground text-xs uppercase block font-semibold">Recommendation</span>
                  <p className="mt-1 text-xs text-muted-foreground">{selectedDetails.recommendation || 'No action required.'}</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="md:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Mandatory Verification Gates ({gatesList.length})</CardTitle>
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
                        <p className="font-semibold text-sm">{gate.gate_id.replace(/_/g, ' ')}</p>
                        <p className="text-xs text-muted-foreground">{gate.reason}</p>
                      </div>
                    </div>
                    <Badge variant="outline" className={`w-28 justify-center font-bold text-xs ${getBadgeClass(gate.status)}`}>
                      {gate.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
