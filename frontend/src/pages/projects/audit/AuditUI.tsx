import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Clock, ShieldCheck, Database, Bot, FileText, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

export default function AuditUI() {
  const { projectId } = useParams<{ projectId: string }>()
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.audit.list(projectId)
      .then(res => setEvents(res.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [projectId])

  const getIcon = (action: string) => {
    if (action.includes('DATASET') || action.includes('UPLOAD')) return <Database className="h-4 w-4" />
    if (action.includes('AGENT') || action.includes('ANALYSIS')) return <Bot className="h-4 w-4" />
    if (action.includes('VERIFICATION')) return <ShieldCheck className="h-4 w-4" />
    if (action.includes('ARTIFACT')) return <FileText className="h-4 w-4" />
    return <Clock className="h-4 w-4" />
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Audit Log</h2>
        <p className="text-muted-foreground">Chronological, immutable audit events recorded in MongoDB Atlas.</p>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : events.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          No audit events logged for this workspace yet.
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {events.map((e: any, i: number) => (
                <div key={i} className="flex gap-4 p-4 hover:bg-muted/30 transition-colors items-start">
                  <div className="flex flex-col items-center gap-1 w-24 pt-1">
                    <span className="text-[10px] font-mono text-muted-foreground">{e.timestamp?.split('T')[1]?.slice(0, 8) || e.timestamp}</span>
                  </div>
                  
                  <div className="mt-1 bg-muted/50 p-2 rounded-full border text-muted-foreground">
                    {getIcon(e.action)}
                  </div>

                  <div className="flex-1 pt-1">
                    <div className="flex items-center justify-between">
                      <p className="font-bold tracking-wide text-sm">{e.action}</p>
                      <Badge variant={e.status === 'error' || e.status === 'FAILED' ? 'destructive' : 'secondary'} className="text-[10px] uppercase">
                        {e.status}
                      </Badge>
                    </div>
                    
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mt-2 text-xs">
                      {e.project_id && (
                        <div>
                          <span className="text-muted-foreground uppercase font-semibold block">Project</span>
                          <span className="font-mono text-xs">{e.project_id}</span>
                        </div>
                      )}
                      {e.dataset_id && (
                        <div>
                          <span className="text-muted-foreground uppercase font-semibold block">Dataset</span>
                          <span className="font-mono text-xs">{e.dataset_id}</span>
                        </div>
                      )}
                      {e.details && (
                        <div>
                          <span className="text-muted-foreground uppercase font-semibold block">Details</span>
                          <span className="text-muted-foreground font-mono truncate block">{JSON.stringify(e.details)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
