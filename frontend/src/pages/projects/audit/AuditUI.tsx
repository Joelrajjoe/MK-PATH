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

  const getIcon = (action?: string) => {
    const act = (action || '').toUpperCase()
    if (act.includes('DATASET') || act.includes('UPLOAD') || act.includes('INGEST') || act.includes('PROFILE')) return <Database className="h-4 w-4 text-sky-500" />
    if (act.includes('AGENT') || act.includes('ANALYSIS') || act.includes('ANALYST') || act.includes('SCIENTIST')) return <Bot className="h-4 w-4 text-purple-500" />
    if (act.includes('VERIFICATION') || act.includes('TOURNAMENT') || act.includes('GATE')) return <ShieldCheck className="h-4 w-4 text-emerald-500" />
    if (act.includes('ARTIFACT') || act.includes('MODEL') || act.includes('HEALING') || act.includes('COMPLETED')) return <FileText className="h-4 w-4 text-amber-500" />
    return <Clock className="h-4 w-4 text-muted-foreground" />
  }

  const formatTime = (iso?: string) => {
    if (!iso) return ''
    try {
      const d = new Date(iso)
      return isNaN(d.getTime()) ? iso : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    } catch {
      return iso
    }
  }

  const formatDate = (iso?: string) => {
    if (!iso) return ''
    try {
      const d = new Date(iso)
      return isNaN(d.getTime()) ? '' : d.toLocaleDateString([], { month: 'short', day: 'numeric' })
    } catch {
      return ''
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Audit Log</h2>
        <p className="text-muted-foreground">Chronological, immutable audit events recorded in database store.</p>
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
              {events.map((e: any, i: number) => {
                const eventName = e.action || e.event_type || 'EVENT'
                const timestamp = e.created_at || e.timestamp
                const isSuccess = e.status === 'ok' || e.status === 'COMPLETED'
                const isError = e.status === 'error' || e.status === 'FAILED'

                return (
                  <div key={i} className="flex gap-4 p-4 hover:bg-muted/30 transition-colors items-start">
                    <div className="flex flex-col items-center gap-0.5 w-24 pt-1 text-right">
                      <span className="text-[11px] font-mono font-semibold text-foreground">{formatTime(timestamp)}</span>
                      <span className="text-[9px] text-muted-foreground">{formatDate(timestamp)}</span>
                    </div>
                    
                    <div className="mt-1 bg-muted/60 p-2 rounded-full border">
                      {getIcon(eventName)}
                    </div>

                    <div className="flex-1 pt-1">
                      <div className="flex items-center justify-between">
                        <p className="font-bold tracking-wide text-sm">{eventName}</p>
                        <Badge
                          variant={isError ? 'destructive' : isSuccess ? 'outline' : 'secondary'}
                          className={`text-[10px] uppercase font-mono ${isSuccess ? 'border-emerald-500 text-emerald-600 bg-emerald-500/10' : ''}`}
                        >
                          {e.status}
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-2 text-xs">
                        {e.project_id && (
                          <div>
                            <span className="text-muted-foreground uppercase font-semibold text-[10px] block">Project</span>
                            <span className="font-mono text-xs">{e.project_id.slice(0, 8)}...</span>
                          </div>
                        )}
                        {e.run_id && (
                          <div>
                            <span className="text-muted-foreground uppercase font-semibold text-[10px] block">Run ID</span>
                            <span className="font-mono text-xs">{e.run_id.slice(0, 8)}...</span>
                          </div>
                        )}
                        {e.dataset_id && (
                          <div>
                            <span className="text-muted-foreground uppercase font-semibold text-[10px] block">Dataset</span>
                            <span className="font-mono text-xs">{e.dataset_id.slice(0, 8)}...</span>
                          </div>
                        )}
                        {e.details && (
                          <div className="col-span-2">
                            <span className="text-muted-foreground uppercase font-semibold text-[10px] block">Details</span>
                            <span className="text-muted-foreground font-mono text-[11px] truncate block max-w-md">{JSON.stringify(e.details)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
