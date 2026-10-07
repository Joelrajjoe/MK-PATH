import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileCode2, CheckCircle, AlertTriangle, Loader2, Package, Terminal, FolderCheck } from 'lucide-react'
import { api } from '@/lib/api'

export default function ArtifactCenter() {
  const { projectId } = useParams<{ projectId: string }>()
  const [artifacts, setArtifacts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedArtifact, setSelectedArtifact] = useState<any | null>(null)

  const loadArtifacts = () => {
    setLoading(true)
    if (projectId) {
      // Fetch both from /artifacts and fallback to /runs
      api.artifacts.list(projectId)
        .then(res => {
          if (res.artifacts && res.artifacts.length > 0) {
            setArtifacts(res.artifacts)
            setSelectedArtifact(res.artifacts[0])
          } else {
            return api.runs.list(projectId).then(runs => {
              const allArts: any[] = []
              runs.forEach(r => {
                if (r.artifacts && Array.isArray(r.artifacts)) {
                  r.artifacts.forEach((a: any) => {
                    allArts.push({
                      ...a,
                      project_id: r.project_id,
                      run_id: a.run_id || r.run_id,
                      created_at: a.validation?.timestamp || r.created_at,
                    })
                  })
                }
              })
              setArtifacts(allArts)
              if (allArts.length > 0) setSelectedArtifact(allArts[0])
            })
          }
        })
        .catch(() => setArtifacts([]))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadArtifacts()
  }, [projectId])

  const verifiedCount = artifacts.filter(a => a.status === 'PASS' || a.validation?.status === 'PASS').length

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Artifact Center</h2>
          <p className="text-muted-foreground">Verified model packages, FastAPI microservices, and serialized deployment artifacts.</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="border-primary/40 bg-primary/5 px-3 py-1 font-mono text-xs">
            {verifiedCount} Verified / {artifacts.length} Total
          </Badge>
          <Button size="sm" variant="outline" onClick={loadArtifacts}>
            Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : artifacts.length === 0 ? (
        <Card className="p-12 text-center text-muted-foreground space-y-3">
          <Package className="h-12 w-12 mx-auto text-muted-foreground/60" />
          <h3 className="font-semibold text-lg text-foreground">No deployment artifacts generated yet</h3>
          <p className="text-sm max-w-md mx-auto">
            Execute the autonomous multi-agent pipeline in the <strong>Agents</strong> tab to train, verify, and package deployable models.
          </p>
        </Card>
      ) : (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Package className="h-4 w-4 text-primary" /> Generated Model Artifacts ({artifacts.length})
                </CardTitle>
                <CardDescription>Select an artifact to inspect deployment specifications and real test inference</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y">
                  {artifacts.map((a, idx) => {
                    const isPass = a.status === 'PASS' || a.validation?.status === 'PASS'
                    const isSelected = selectedArtifact?.run_id === a.run_id && selectedArtifact?.model_version === a.model_version

                    return (
                      <div
                        key={idx}
                        onClick={() => setSelectedArtifact(a)}
                        className={`p-4 flex items-center justify-between cursor-pointer transition-colors ${
                          isSelected ? 'bg-primary/5 border-l-4 border-l-primary' : 'hover:bg-muted/40'
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm">{a.model_version || 'Trained Model'}</span>
                            <Badge
                              variant={isPass ? 'outline' : 'destructive'}
                              className={`text-[10px] uppercase font-mono ${
                                isPass ? 'border-emerald-500 text-emerald-600 bg-emerald-500/10' : ''
                              }`}
                            >
                              {isPass ? <CheckCircle className="h-3 w-3 mr-1 inline" /> : <AlertTriangle className="h-3 w-3 mr-1 inline" />}
                              {isPass ? 'PASS' : a.status || 'FAILED'}
                            </Badge>
                          </div>
                          <p className="text-xs font-mono text-muted-foreground truncate max-w-md">
                            Run: {a.run_id}
                          </p>
                          {a.validation?.test_prediction && (
                            <p className="text-xs text-foreground">
                              Test Prediction: <span className="font-mono font-semibold text-emerald-600">{a.validation.test_prediction}</span>
                              {a.validation.feature_count && (
                                <span className="text-muted-foreground ml-2">({a.validation.feature_count} features)</span>
                              )}
                            </p>
                          )}
                        </div>

                        <div className="text-right text-xs text-muted-foreground font-mono">
                          {a.created_at ? new Date(a.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            {selectedArtifact ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <FolderCheck className="h-4 w-4 text-emerald-500" /> Deployment Bundle
                  </CardTitle>
                  <CardDescription>Verified artifact filesystem layout</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 text-xs">
                  <div>
                    <span className="font-semibold text-muted-foreground block uppercase text-[10px] mb-1">Model Name</span>
                    <span className="font-medium text-foreground text-sm">{selectedArtifact.model_version || 'Model'}</span>
                  </div>

                  <div>
                    <span className="font-semibold text-muted-foreground block uppercase text-[10px] mb-1">Filesystem Path</span>
                    <span className="font-mono bg-muted p-2 rounded block break-all text-[11px] text-foreground">
                      {selectedArtifact.artifact_dir || 'E:\\MKPATH\\artifacts\\...'}
                    </span>
                  </div>

                  <div>
                    <span className="font-semibold text-muted-foreground block uppercase text-[10px] mb-1.5">Package Contents</span>
                    <div className="space-y-1 font-mono text-[11px] bg-muted/40 p-2.5 rounded border">
                      <div className="flex items-center gap-2 text-foreground">
                        <FileCode2 className="h-3.5 w-3.5 text-primary" />
                        <span>model/model.pkl</span>
                      </div>
                      <div className="flex items-center gap-2 text-foreground">
                        <FileCode2 className="h-3.5 w-3.5 text-sky-500" />
                        <span>api/main.py (FastAPI App)</span>
                      </div>
                      <div className="flex items-center gap-2 text-foreground">
                        <FileCode2 className="h-3.5 w-3.5 text-sky-500" />
                        <span>api/schema.py (Pydantic Models)</span>
                      </div>
                      <div className="flex items-center gap-2 text-foreground">
                        <FileCode2 className="h-3.5 w-3.5 text-purple-500" />
                        <span>MODEL_CARD.md</span>
                      </div>
                      <div className="flex items-center gap-2 text-foreground">
                        <FileCode2 className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>metadata.json</span>
                      </div>
                    </div>
                  </div>

                  {selectedArtifact.validation?.reason && (
                    <div className="p-2.5 bg-red-500/10 border border-red-500/20 rounded text-red-600 font-mono text-[10px]">
                      {selectedArtifact.validation.reason}
                    </div>
                  )}

                  <div>
                    <span className="font-semibold text-muted-foreground block uppercase text-[10px] mb-1">Serve Command</span>
                    <div className="bg-muted p-2 rounded font-mono text-[11px] flex items-center gap-2">
                      <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
                      <code>uvicorn api.main:app --port 8080</code>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="p-8 text-center text-muted-foreground text-xs">
                Select an artifact to view deployment details.
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
