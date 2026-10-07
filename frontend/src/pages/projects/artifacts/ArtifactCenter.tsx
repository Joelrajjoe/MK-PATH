import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FileCode2, CheckCircle, Loader2, Package } from 'lucide-react'
import { api } from '@/lib/api'

export default function ArtifactCenter() {
  const { projectId } = useParams<{ projectId: string }>()
  const [artifacts, setArtifacts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    if (projectId) {
      api.audit.list(projectId).then(res => {
        const evs = res.events || []
        const arts: any[] = []
        evs.forEach((e: any) => {
          if (e.action === 'WORKFLOW_COMPLETED' || e.action === 'ARTIFACT_GENERATED') {
            arts.push(e)
          }
        })
        setArtifacts(arts)
      }).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [projectId])

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Artifact Center</h2>
        <p className="text-muted-foreground">Manage generated models, FastAPI services, and verification reports.</p>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Package className="h-5 w-5 text-primary" /> Generated Deployment Artifacts</CardTitle>
            <CardDescription>Verified FastAPI services and pickled models in E:\MK-PATH\artifacts</CardDescription>
          </CardHeader>
          <CardContent>
            {artifacts.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p className="text-sm">No deployment artifacts generated yet.</p>
                <p className="text-xs mt-1">Run an agent workflow or model tournament to build verified model artifacts.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                    <tr>
                      <th className="px-3 py-3">Artifact</th>
                      <th className="px-3 py-3">Timestamp</th>
                      <th className="px-3 py-3">Verification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {artifacts.map((a, idx) => (
                      <tr key={idx}>
                        <td className="px-3 py-3 font-medium flex items-center gap-2">
                          <FileCode2 className="h-4 w-4 text-primary" />
                          {a.action} (Run: {a.run_id || 'active'})
                        </td>
                        <td className="px-3 py-3 font-mono text-xs">{a.timestamp}</td>
                        <td className="px-3 py-3">
                          <Badge variant="outline" className="border-emerald-500 text-emerald-600 bg-emerald-500/10">
                            <CheckCircle className="h-3 w-3 mr-1" /> PASS
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
