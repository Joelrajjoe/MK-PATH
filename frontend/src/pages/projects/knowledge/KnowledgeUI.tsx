import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertCircle, CheckCircle, Edit2, Loader2, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'

interface KnowledgeUIProps {
  projectId?: string
}

export default function KnowledgeUI({ projectId }: KnowledgeUIProps) {
  const [goal, setGoal] = useState<string>('')
  const [isEditingGoal, setIsEditingGoal] = useState(false)
  const [datasets, setDatasets] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('')
  const [semanticContext, setSemanticContext] = useState<any>(null)
  const [ambiguitiesData, setAmbiguitiesData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [building, setBuilding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resolvingId, setResolvingId] = useState<string | null>(null)
  const [selectedChoices, setSelectedChoices] = useState<Record<string, string>>({})

  // Load project details & datasets
  useEffect(() => {
    if (projectId) {
      api.projects.get(projectId)
        .then(p => {
          if (p.businessGoal) setGoal(p.businessGoal)
        })
        .catch(() => {})

      api.datasets.list(projectId)
        .then(ds => {
          setDatasets(ds)
          if (ds.length > 0) {
            setSelectedDatasetId(ds[0].dataset_id || ds[0].id)
          }
        })
        .catch(err => setError(err.message))
    }
  }, [projectId])

  // Load semantic context when dataset is selected
  const fetchSemanticData = async (dsId: string) => {
    if (!dsId) return
    setLoading(true)
    setError(null)
    try {
      const ctx = await api.semantic.get(dsId)
      setSemanticContext(ctx)
      if (ctx) {
        const ambs = await api.semantic.getAmbiguities(dsId)
        setAmbiguitiesData(ambs)
      } else {
        setAmbiguitiesData(null)
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Failed to load semantic knowledge.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedDatasetId) {
      fetchSemanticData(selectedDatasetId)
    }
  }, [selectedDatasetId])

  const handleBuildSemantic = async () => {
    if (!selectedDatasetId) return
    setBuilding(true)
    setError(null)
    try {
      const ctx = await api.semantic.build(selectedDatasetId, goal)
      setSemanticContext(ctx)
      const ambs = await api.semantic.getAmbiguities(selectedDatasetId)
      setAmbiguitiesData(ambs)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Failed to build semantic context.')
    } finally {
      setBuilding(false)
    }
  }

  const handleResolveAmbiguity = async (questionId: string) => {
    const choice = selectedChoices[questionId]
    if (!choice) return
    setResolvingId(questionId)
    try {
      await api.semantic.resolve(questionId, choice)
      // Refresh semantic context and ambiguities after resolution
      await fetchSemanticData(selectedDatasetId)
    } catch (err: any) {
      alert(err.message || 'Failed to resolve ambiguity')
    } finally {
      setResolvingId(null)
    }
  }

  return (
    <div className="space-y-8">
      {/* Dataset Selector */}
      {datasets.length > 1 && (
        <div className="flex items-center gap-4 p-4 bg-muted/30 rounded-lg border">
          <Label htmlFor="ds-select" className="font-medium">Selected Dataset:</Label>
          <select
            id="ds-select"
            className="border rounded px-3 py-1 text-sm bg-background"
            value={selectedDatasetId}
            onChange={(e) => setSelectedDatasetId(e.target.value)}
          >
            {datasets.map((d: any) => (
              <option key={d.dataset_id || d.id} value={d.dataset_id || d.id}>
                {d.original_filename || d.table_name || d.name} ({d.dataset_id || d.id})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* 1. Business Goal */}
      <Card>
        <CardHeader>
          <CardTitle>1. Business Goal</CardTitle>
          <CardDescription>The primary objective for this workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          {isEditingGoal ? (
            <div className="flex gap-2">
              <Input value={goal} onChange={e => setGoal(e.target.value)} placeholder="e.g. Predict customer churn within 30 days" />
              <Button onClick={() => setIsEditingGoal(false)}>Save</Button>
            </div>
          ) : (
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border">
              <p className="text-lg font-medium">{goal || 'No business goal specified.'}</p>
              <Button variant="ghost" size="icon" onClick={() => setIsEditingGoal(true)}>
                <Edit2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Status / Loading State */}
      {loading && (
        <Card className="p-8 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-2" />
          <p className="text-muted-foreground">Loading semantic knowledge from backend...</p>
        </Card>
      )}

      {error && (
        <Card className="border-red-500/50 bg-red-500/5 p-4 text-red-600">
          <AlertCircle className="h-5 w-5 inline mr-2" />
          {error}
        </Card>
      )}

      {/* No Semantic Knowledge Available Yet */}
      {!loading && !semanticContext && selectedDatasetId && (
        <Card className="p-8 text-center space-y-4">
          <Sparkles className="h-10 w-10 text-muted-foreground mx-auto" />
          <div>
            <h3 className="text-lg font-semibold">No semantic knowledge available yet</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Trigger semantic processing to build dataset concepts, identify business terms, and resolve ambiguities.
            </p>
          </div>
          <Button onClick={handleBuildSemantic} disabled={building}>
            {building ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" /> Processing Semantic Context...
              </>
            ) : (
              'Generate Semantic Knowledge'
            )}
          </Button>
        </Card>
      )}

      {/* 2. Ambiguities Section (Real backend state) */}
      {!loading && ambiguitiesData && ambiguitiesData.questions && ambiguitiesData.questions.length > 0 && (
        <div className="space-y-4">
          {ambiguitiesData.questions.map((q: any) => (
            <Card key={q.question_id} className="border-orange-500/50 bg-orange-500/5">
              <CardHeader>
                <CardTitle className="text-orange-600 flex items-center gap-2 text-base">
                  <AlertCircle className="h-5 w-5" /> AMBIGUITY DETECTED ({q.kind})
                </CardTitle>
                <CardDescription>{q.question}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {q.options && q.options.length > 0 && (
                  <div>
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider">Select Interpretation</Label>
                    <div className="mt-2 space-y-2">
                      {q.options.map((opt: any, idx: number) => {
                        const optVal = typeof opt === 'string' ? opt : opt.label
                        const optDesc = typeof opt === 'object' ? opt.description : ''
                        return (
                          <label key={idx} className="flex items-start gap-2 p-2 rounded border bg-background hover:bg-muted/50 cursor-pointer text-sm">
                            <input
                              type="radio"
                              name={`q_${q.question_id}`}
                              value={optVal}
                              checked={selectedChoices[q.question_id] === optVal}
                              onChange={() => setSelectedChoices({ ...selectedChoices, [q.question_id]: optVal })}
                              className="mt-1"
                            />
                            <div>
                              <div className="font-medium">{optVal}</div>
                              {optDesc && <div className="text-xs text-muted-foreground">{optDesc}</div>}
                            </div>
                          </label>
                        )
                      })}
                    </div>
                  </div>
                )}
                <div className="pt-2">
                  <Button
                    className="bg-orange-600 hover:bg-orange-700"
                    disabled={!selectedChoices[q.question_id] || resolvingId === q.question_id}
                    onClick={() => handleResolveAmbiguity(q.question_id)}
                  >
                    {resolvingId === q.question_id ? 'Resolving...' : 'Resolve Ambiguity'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 3. Dataset Concepts Table (Real backend response) */}
      {!loading && semanticContext && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Dataset Concepts</CardTitle>
              <CardDescription>
                Workflow Status: <span className="font-mono font-semibold">{semanticContext.workflow_status}</span> | Confidence Score: {(semanticContext.confidence * 100).toFixed(1)}%
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={handleBuildSemantic} disabled={building}>
              {building ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Re-process'}
            </Button>
          </CardHeader>
          <CardContent>
            {(!semanticContext.concepts || semanticContext.concepts.length === 0) ? (
              <p className="text-sm text-muted-foreground p-4 text-center">No concepts extracted yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                    <tr>
                      <th className="px-4 py-3">Concept Name</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Source</th>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3">Confidence</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {semanticContext.concepts.map((c: any, i: number) => (
                      <tr key={c.id || i}>
                        <td className="px-4 py-3 font-medium">{c.name}</td>
                        <td className="px-4 py-3 text-xs font-mono bg-muted/30">{c.type}</td>
                        <td className="px-4 py-3 text-xs font-mono bg-muted/30">{c.source}</td>
                        <td className="px-4 py-3 text-xs max-w-xs truncate">{c.description || '-'}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-2 bg-secondary rounded-full overflow-hidden">
                              <div
                                className={`h-2 rounded-full ${c.confidence >= 0.8 ? 'bg-green-500' : 'bg-orange-500'}`}
                                style={{ width: `${(c.confidence || 0) * 100}%` }}
                              />
                            </div>
                            <span className="text-xs">{((c.confidence || 0) * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {c.status === 'confirmed' || c.status === 'ready' ? (
                            <span className="flex items-center gap-1 text-green-600 text-xs"><CheckCircle className="h-3 w-3" /> Confirmed</span>
                          ) : (
                            <span className="flex items-center gap-1 text-orange-600 text-xs"><AlertCircle className="h-3 w-3" /> {c.status}</span>
                          )}
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

      {/* 4. Business Terms, Metrics, Dimensions, Relationships (Real backend context) */}
      {!loading && semanticContext && (
        <div className="grid md:grid-cols-2 gap-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Business Terms ({semanticContext.business_terms?.length || 0})</CardTitle></CardHeader>
            <CardContent className="text-sm">
              {semanticContext.business_terms?.length ? (
                <ul className="list-disc list-inside space-y-1">
                  {semanticContext.business_terms.map((t: any, idx: number) => (
                    <li key={idx}><strong>{t.name}</strong>: {t.description || 'No definition'}</li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground text-xs">No business terms identified.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Metrics ({semanticContext.metrics?.length || 0})</CardTitle></CardHeader>
            <CardContent className="text-sm">
              {semanticContext.metrics?.length ? (
                <ul className="list-disc list-inside space-y-1">
                  {semanticContext.metrics.map((m: any, idx: number) => (
                    <li key={idx}><strong>{m.name}</strong> ({m.source})</li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground text-xs">No metrics identified.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Dimensions ({semanticContext.dimensions?.length || 0})</CardTitle></CardHeader>
            <CardContent className="text-sm">
              {semanticContext.dimensions?.length ? (
                <ul className="list-disc list-inside space-y-1">
                  {semanticContext.dimensions.map((d: any, idx: number) => (
                    <li key={idx}><strong>{d.name}</strong> ({d.source})</li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground text-xs">No dimensions identified.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Relationships ({semanticContext.relationships?.length || 0})</CardTitle></CardHeader>
            <CardContent className="text-sm">
              {semanticContext.relationships?.length ? (
                <ul className="list-disc list-inside space-y-1">
                  {semanticContext.relationships.map((r: any, idx: number) => (
                    <li key={idx}>{r.subject} &rarr; <em>{r.predicate}</em> &rarr; {r.object}</li>
                  ))}
                </ul>
              ) : <p className="text-muted-foreground text-xs">No relationships identified.</p>}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
