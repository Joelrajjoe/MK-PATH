import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertCircle, CheckCircle, ShieldAlert } from 'lucide-react'

export default function TemporalLeakage() {
  const overallStatus = 'FAIL'

  const features = [
    { name: 'cancellation_timestamp', predictionTime: '2025-01-01', availableTime: '2025-01-10', targetTime: '2025-01-05', risk: 'FAIL', reason: 'Available after prediction time' },
    { name: 'last_login', predictionTime: '2025-01-01', availableTime: '2024-12-30', targetTime: '2025-01-05', risk: 'PASS', reason: 'Available before prediction' },
    { name: 'support_tickets_count', predictionTime: '2025-01-01', availableTime: '2025-01-01', targetTime: '2025-01-05', risk: 'WARNING', reason: 'Available exact day of prediction' }
  ]

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Temporal Leakage Verification</h2>
        <p className="text-muted-foreground">Automated checks ensuring feature availability at prediction time.</p>
      </div>

      <Card className="border-destructive/50 bg-destructive/5">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-destructive">
            <ShieldAlert className="h-6 w-6" /> TEMPORAL LEAKAGE CHECK: {overallStatus}
          </CardTitle>
          <CardDescription className="text-destructive/80 font-medium">
            DEPLOYMENT BLOCKED. Frontend cannot override this backend verification decision.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Feature Availability Timeline</CardTitle>
          <CardDescription>Visual mapping of problematic features against temporal anchors.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-muted/30 rounded-lg border font-mono text-sm space-y-4 overflow-x-auto">
            <div>
              <p className="mb-2 text-muted-foreground">Example: cancellation_timestamp (FAIL)</p>
              <div className="flex items-center text-xs">
                <span className="w-24 text-right pr-4">Prediction</span>
                <span>──────────●─────── (2025-01-01)</span>
              </div>
              <div className="flex items-center text-xs">
                <span className="w-24 text-right pr-4">Target</span>
                <span>────────────●───── (2025-01-05)</span>
              </div>
              <div className="flex items-center text-xs text-destructive">
                <span className="w-24 text-right pr-4">Feature Event</span>
                <span>─────────────────● (2025-01-10)</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Feature Table</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                <tr>
                  <th className="px-4 py-3">Feature</th>
                  <th className="px-4 py-3">Prediction Time</th>
                  <th className="px-4 py-3">Available Time</th>
                  <th className="px-4 py-3">Target Time</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {features.map((f, i) => (
                  <tr key={i} className={f.risk === 'FAIL' ? 'bg-destructive/5' : ''}>
                    <td className="px-4 py-3 font-medium">{f.name}</td>
                    <td className="px-4 py-3">{f.predictionTime}</td>
                    <td className="px-4 py-3">{f.availableTime}</td>
                    <td className="px-4 py-3">{f.targetTime}</td>
                    <td className="px-4 py-3">
                      <span className={`flex items-center gap-1 text-xs font-bold ${
                        f.risk === 'FAIL' ? 'text-destructive' :
                        f.risk === 'WARNING' ? 'text-orange-500' : 'text-green-600'
                      }`}>
                        {f.risk === 'FAIL' ? <AlertCircle className="h-3 w-3" /> :
                         f.risk === 'WARNING' ? <AlertCircle className="h-3 w-3" /> :
                         <CheckCircle className="h-3 w-3" />}
                        {f.risk}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{f.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
        <CardFooter className="flex gap-2 bg-muted/20 border-t p-4">
          <Button variant="default" className="bg-destructive hover:bg-destructive/90">Quarantine Feature</Button>
          <Button variant="outline">View Evidence</Button>
          <Button variant="outline">Return to Feature Selection</Button>
        </CardFooter>
      </Card>
    </div>
  )
}
