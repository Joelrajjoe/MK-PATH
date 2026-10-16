import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { GitCommit, ShieldCheck, ShieldAlert, CheckCircle, RefreshCw, ArrowDown, Database, Cpu, Wrench } from 'lucide-react'
import { api } from '@/lib/api'

interface Props {
  runId: string
  projectId?: string
}

export const LineageExplorer: React.FC<Props> = ({ runId }) => {

  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<any>(null)

  const loadEvents = async () => {
    if (!runId) return
    setLoading(true)
    try {
      const data = await api.attestations.getRunLineage(runId)
      setEvents(data || [])
    } catch (err) {
      console.error('Failed to load lineage events:', err)
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEvents()
  }, [runId])

  const handleVerifyChain = async () => {
    setVerifying(true)
    try {
      const res = await api.attestations.verifyRunLineage(runId)
      setVerifyResult(res)
    } catch (err: any) {
      setVerifyResult({
        chain_valid: false,
        errors: [err.message || 'Verification request failed'],
      })
    } finally {
      setVerifying(false)
    }
  }

  const getEventIcon = (type: string) => {
    if (type.includes('INGESTION')) return <Database className="h-4 w-4 text-blue-400" />
    if (type.includes('HEALING')) return <Wrench className="h-4 w-4 text-amber-400" />
    if (type.includes('VERIFICATION') || type.includes('PMSG')) return <CheckCircle className="h-4 w-4 text-emerald-400" />
    if (type.includes('ATTESTATION')) return <ShieldCheck className="h-4 w-4 text-indigo-400" />
    return <Cpu className="h-4 w-4 text-purple-400" />
  }

  return (
    <Card className="border border-border/50 bg-card/70 backdrop-blur shadow-sm">
      <CardHeader className="pb-3 border-b border-border/40">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <GitCommit className="h-5 w-5 text-indigo-400" />
              <CardTitle className="text-base font-semibold font-mono tracking-tight">
                Tamper-Evident Healing Lineage Graph
              </CardTitle>
              <Badge variant="outline" className="font-mono text-xs">
                {events.length} Chained Event(s)
              </Badge>
            </div>
            <CardDescription className="text-xs text-muted-foreground mt-0.5">
              Hash-chained provenance: <span className="font-mono text-foreground/80">SHA256(canonical || prev_hash)</span>
            </CardDescription>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleVerifyChain}
            disabled={verifying || events.length === 0}
            className="h-8 gap-1.5 text-xs font-mono font-medium"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${verifying ? 'animate-spin' : ''}`} />
            {verifying ? 'Verifying Chain...' : 'Verify Hash Continuity'}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Chain Verification Result */}
        {verifyResult && (
          <div
            className={`p-3 rounded-md border font-mono text-xs ${
              verifyResult.chain_valid
                ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200'
                : 'bg-red-950/40 border-red-800 text-red-200'
            }`}
          >
            <div className="flex items-center gap-2 font-semibold">
              {verifyResult.chain_valid ? (
                <CheckCircle className="h-4 w-4 text-emerald-400" />
              ) : (
                <ShieldAlert className="h-4 w-4 text-red-400" />
              )}
              Chain Hash Continuity: {verifyResult.chain_valid ? 'INTACT & UNBROKEN' : 'LINEAGE BROKEN'}
            </div>
            {verifyResult.head_event_hash && (
              <div className="mt-1 text-[11px] opacity-90 truncate">
                Head Event Hash: {verifyResult.head_event_hash}
              </div>
            )}
            {verifyResult.errors?.length > 0 && (
              <ul className="list-disc pl-4 mt-1 text-red-300 font-sans text-xs">
                {verifyResult.errors.map((e: string, i: number) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Timeline Event Cards */}
        {loading ? (
          <div className="py-8 text-center text-muted-foreground text-xs font-mono">
            Loading lineage event graph...
          </div>
        ) : events.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground text-xs font-mono">
            No lineage events recorded yet for this run.
          </div>
        ) : (
          <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-border/60">
            {events.map((ev: any, idx: number) => (
              <div key={ev.event_id || idx} className="relative">
                {/* Node icon dot */}
                <div className="absolute -left-6 top-1.5 h-5 w-5 rounded-full bg-background border border-border flex items-center justify-center shadow-xs">
                  {getEventIcon(ev.event_type)}
                </div>

                <div className="p-3 rounded-md bg-muted/20 border border-border/40 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-foreground">
                        #{ev.sequence_number} {ev.event_type}
                      </span>
                      <span className="text-[10px] font-mono text-muted-foreground">
                        ({ev.actor})
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : ''}
                    </span>
                  </div>

                  {/* Hash Chain Display */}
                  <div className="font-mono text-[10px] space-y-0.5 bg-background/60 p-2 rounded border border-border/20">
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>Prev Hash:</span>
                      <span className="truncate max-w-[260px] opacity-80">{ev.previous_event_hash}</span>
                    </div>
                    <div className="flex items-center justify-between text-foreground/90 font-medium">
                      <span>Event Hash:</span>
                      <span className="truncate max-w-[260px] text-cyan-300">{ev.event_hash}</span>
                    </div>
                  </div>

                  {/* Details preview */}
                  {ev.details && Object.keys(ev.details).length > 0 && (
                    <div className="text-[11px] text-muted-foreground font-mono">
                      {Object.entries(ev.details).map(([k, v]) => (
                        <span key={k} className="inline-block mr-3">
                          <strong className="text-foreground/80">{k}:</strong> {String(v)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {idx < events.length - 1 && (
                  <div className="flex justify-center my-1 opacity-40">
                    <ArrowDown className="h-3 w-3" />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default LineageExplorer
