import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Clock, ShieldCheck, Database, Bot, FileText, User } from 'lucide-react'

export default function AuditUI() {
  const events = [
    { time: '10:01:12', actor: 'user_joel', agent: '--', action: 'DATASET UPLOADED', status: 'COMPLETED', evidence: 'customers.csv (1MB)', runId: 'run_a1b2', type: 'Data' },
    { time: '10:02:45', actor: 'system', agent: 'Profiler', action: 'PROFILE COMPLETED', status: 'COMPLETED', evidence: '12 cols, 5000 rows', runId: 'run_a1b2', type: 'Data' },
    { time: '10:03:10', actor: 'system', agent: 'Semantic Resolver', action: 'SEMANTIC AMBIGUITY DETECTED', status: 'PAUSED', evidence: 'Column: status', runId: 'run_c3d4', type: 'Agents' },
    { time: '10:04:05', actor: 'user_joel', agent: '--', action: 'USER DECISION RECORDED', status: 'COMPLETED', evidence: 'status=4 means Other', runId: 'run_c3d4', type: 'Healing' },
    { time: '10:05:30', actor: 'system', agent: 'Data Analyst', action: 'DATA ANALYST COMPLETED', status: 'COMPLETED', evidence: 'Plan approved', runId: 'run_e5f6', type: 'Agents' },
    { time: '10:07:00', actor: 'system', agent: 'Verification', action: 'TEMPORAL LEAKAGE CHECK', status: 'FAILED', evidence: 'cancellation_timestamp blocked', runId: 'run_v7g8', type: 'Verification' },
    { time: '10:07:15', actor: 'system', agent: 'Healing', action: 'FEATURE QUARANTINED', status: 'COMPLETED', evidence: 'cancellation_timestamp removed', runId: 'run_v7g8', type: 'Healing' },
    { time: '10:08:22', actor: 'system', agent: 'Model Builder', action: 'MODEL TOURNAMENT BLOCKED', status: 'BLOCKED', evidence: 'Mandatory verification gate failed', runId: 'run_m9h0', type: 'Verification' },
  ]

  const getIcon = (type: string) => {
    switch (type) {
      case 'Data': return <Database className="h-4 w-4" />
      case 'Agents': return <Bot className="h-4 w-4" />
      case 'Verification': return <ShieldCheck className="h-4 w-4" />
      case 'Artifacts': return <FileText className="h-4 w-4" />
      case 'Healing': return <User className="h-4 w-4" />
      default: return <Clock className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Audit Log</h2>
          <p className="text-muted-foreground">Chronological, immutable record of all system events.</p>
        </div>
        <div className="w-48">
          <select className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
            <option value="all">All Events</option>
            <option value="agents">Agents</option>
            <option value="data">Data</option>
            <option value="verification">Verification</option>
            <option value="healing">Healing</option>
            <option value="artifacts">Artifacts</option>
          </select>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="divide-y border-t mt-4">
            {events.map((e, i) => (
              <div key={i} className="flex gap-4 p-4 hover:bg-muted/30 transition-colors items-start">
                <div className="flex flex-col items-center gap-2 w-16 pt-1">
                  <span className="text-xs font-mono text-muted-foreground">{e.time}</span>
                  <div className="h-8 w-px bg-border my-1"></div>
                </div>
                
                <div className="mt-1 bg-muted/50 p-2 rounded-full border text-muted-foreground">
                  {getIcon(e.type)}
                </div>

                <div className="flex-1 pt-1">
                  <div className="flex items-center justify-between">
                    <p className="font-bold tracking-wide text-sm">{e.action}</p>
                    <Badge variant={e.status === 'FAILED' || e.status === 'BLOCKED' ? 'destructive' : e.status === 'PAUSED' ? 'outline' : 'secondary'} className="text-[10px]">
                      {e.status}
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-3 text-xs">
                    <div>
                      <span className="text-muted-foreground uppercase font-semibold block mb-0.5">Actor</span>
                      <span className="font-mono">{e.actor}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground uppercase font-semibold block mb-0.5">Agent</span>
                      <span className="font-medium">{e.agent}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground uppercase font-semibold block mb-0.5">Run ID</span>
                      <span className="font-mono text-primary">{e.runId}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground uppercase font-semibold block mb-0.5">Evidence</span>
                      <span className="text-muted-foreground truncate block max-w-[200px]" title={e.evidence}>{e.evidence}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
