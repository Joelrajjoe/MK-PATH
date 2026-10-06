import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle, ShieldAlert, UserCheck, Activity, ShieldCheck, Download } from 'lucide-react'

export default function VerificationCenter() {
  const [selectedGate, setSelectedGate] = useState<string | null>(null)

  const gates = [
    { id: 'data_quality', name: 'Data Quality', status: 'PASS', severity: 'HIGH', evidence: 4, time: '10:02 AM', desc: 'Checks missing values, outliers, and duplicates against thresholds.' },
    { id: 'semantic', name: 'Semantic Validity', status: 'PASS', severity: 'HIGH', evidence: 2, time: '10:04 AM', desc: 'Validates business domain mappings.' },
    { id: 'leakage', name: 'Temporal Leakage', status: 'FAIL', severity: 'CRITICAL', evidence: 1, time: '10:07 AM', desc: 'Ensures features are available before prediction time.' },
    { id: 'causal', name: 'Causal Validation', status: 'WARNING', severity: 'MEDIUM', evidence: 3, time: '10:10 AM', desc: 'Validates estimated treatment effects.' },
    { id: 'explainability', name: 'Explainability', status: 'PASS', severity: 'HIGH', evidence: 5, time: '10:15 AM', desc: 'Checks SHAP/LIME global and local explanations.' },
    { id: 'fairness', name: 'Fairness', status: 'HUMAN REVIEW', severity: 'CRITICAL', evidence: 2, time: '10:16 AM', desc: 'Disparate impact analysis across protected cohorts.' },
    { id: 'performance', name: 'Performance', status: 'PASS', severity: 'HIGH', evidence: 8, time: '10:18 AM', desc: 'Latency and throughput benchmarks.' },
    { id: 'artifact', name: 'Artifact Validation', status: 'BLOCKED', severity: 'HIGH', evidence: 0, time: '--', desc: 'Ensures all generated artifacts are complete and signed.' },
  ]

  // eslint-disable-next-line prefer-const
  let overallState = 'BLOCKED'

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS': return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'WARNING': return <AlertCircle className="h-5 w-5 text-orange-500" />
      case 'FAIL': return <ShieldAlert className="h-5 w-5 text-destructive" />
      case 'HUMAN REVIEW': return <UserCheck className="h-5 w-5 text-purple-500" />
      case 'BLOCKED': return <ShieldAlert className="h-5 w-5 text-muted-foreground" />
      default: return <Activity className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getBadgeVariant = (status: string) => {
    switch (status) {
      case 'PASS': return 'default'
      case 'WARNING': return 'secondary'
      case 'FAIL': return 'destructive'
      case 'HUMAN REVIEW': return 'outline'
      default: return 'secondary'
    }
  }

  const selectedDetails = gates.find(g => g.id === selectedGate)

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">MK-Path Verification Center</h2>
        <p className="text-muted-foreground">Central trust and control interface for deployment readiness.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-1 space-y-6">
          <Card className={`border-2 ${overallState === 'BLOCKED' ? 'border-destructive bg-destructive/5' : 'border-green-500 bg-green-50'}`}>
            <CardHeader className="pb-4">
              <CardTitle className={`flex items-center gap-2 ${overallState === 'BLOCKED' ? 'text-destructive' : 'text-green-700'}`}>
                <ShieldCheck className="h-6 w-6" /> Deployment Readiness
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-black uppercase tracking-widest">{overallState}</div>
              {overallState === 'BLOCKED' && (
                <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded text-sm text-destructive font-medium">
                  Reason: Temporal Leakage (FAIL), Fairness (HUMAN REVIEW)
                </div>
              )}
            </CardContent>
            <CardFooter>
              <Button className="w-full" disabled={overallState !== 'READY'} variant={overallState === 'READY' ? 'default' : 'outline'}>
                <Download className="h-4 w-4 mr-2" /> Generate Deployment Artifact
              </Button>
            </CardFooter>
          </Card>

          {selectedDetails && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {selectedDetails.name}
                  {getStatusIcon(selectedDetails.status)}
                </CardTitle>
                <CardDescription>Gate Details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <span className="text-muted-foreground text-xs uppercase block">What was checked</span>
                  <p className="font-medium">{selectedDetails.desc}</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div><span className="text-muted-foreground text-xs uppercase block">Threshold</span><p className="font-mono">P99 &lt; 50ms</p></div>
                  <div><span className="text-muted-foreground text-xs uppercase block">Observed</span><p className="font-mono">45ms</p></div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs uppercase block">Evidence</span>
                  <div className="bg-muted p-2 mt-1 rounded text-xs font-mono">
                    Run ID: run_b2k19<br/>
                    {selectedDetails.evidence} pieces of evidence attached.
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs uppercase block">Reason & Recommendation</span>
                  <p className="mt-1">Backend verification determined status based on deterministic constraints. Review logs for override context.</p>
                </div>
              </CardContent>
              <CardFooter className="flex flex-col gap-2 border-t pt-4">
                {selectedDetails.status === 'HUMAN REVIEW' ? (
                  <Button className="w-full bg-purple-600 hover:bg-purple-700">Provide Human Decision</Button>
                ) : (
                  <Button className="w-full" variant="outline">Acknowledge</Button>
                )}
                <Button className="w-full" variant="ghost">Request Re-run</Button>
              </CardFooter>
            </Card>
          )}
        </div>

        <div className="md:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Mandatory Verification Gates</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3">
                {gates.map(gate => (
                  <div 
                    key={gate.id} 
                    className={`flex items-center justify-between p-4 border rounded-lg cursor-pointer transition-colors hover:bg-muted/50 ${selectedGate === gate.id ? 'border-primary shadow-sm bg-primary/5' : ''}`}
                    onClick={() => setSelectedGate(gate.id)}
                  >
                    <div className="flex items-center gap-4">
                      {getStatusIcon(gate.status)}
                      <div>
                        <p className="font-semibold">{gate.name}</p>
                        <p className="text-xs text-muted-foreground">{gate.desc}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground font-mono">{gate.time}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{gate.evidence} evidence</p>
                      </div>
                      <Badge variant={getBadgeVariant(gate.status)} className="w-24 justify-center">
                        {gate.status}
                      </Badge>
                    </div>
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
