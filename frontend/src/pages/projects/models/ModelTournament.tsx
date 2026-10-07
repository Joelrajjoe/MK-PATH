import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Trophy, CheckCircle, BarChart3, Loader2, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'

export default function ModelTournament() {
  const { projectId } = useParams<{ projectId: string }>()
  const [datasets, setDatasets] = useState<any[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [targetCol, setTargetCol] = useState('')
  const [columns, setColumns] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (projectId) {
      api.datasets.list(projectId).then(ds => {
        setDatasets(ds)
        if (ds.length > 0) {
          const firstId = ds[0].id || ds[0].dataset_id
          if (firstId) setSelectedDatasetId(firstId)
        }
      })
    }
  }, [projectId])

  useEffect(() => {
    if (selectedDatasetId) {
      api.datasets.schema(selectedDatasetId).then(s => {
        if (s && s.columns) {
          const colNames = s.columns.map((c: any) => c.name)
          setColumns(colNames)
          if (colNames.length > 0) setTargetCol(colNames[colNames.length - 1])
        }
      }).catch(() => {})
    }
  }, [selectedDatasetId])

  const handleRunTournament = async () => {
    if (!selectedDatasetId || !targetCol) return
    setRunning(true)
    setError(null)
    setResults(null)
    try {
      const res = await api.models.tournament(selectedDatasetId, targetCol, false)
      setResults(res)
      if (res.error) {
        setError(res.message || res.error)
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Model tournament failed.')
    } finally {
      setRunning(false)
    }
  }

  const selectedModel = results?.selected_model

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Model Tournament</h2>
          <p className="text-muted-foreground">Train and compare scikit-learn & LightGBM models on real dataset columns.</p>
        </div>
        <div className="flex items-center gap-3">
          {datasets.length > 0 && (
            <select
              className="border rounded px-3 py-1.5 text-sm bg-background"
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
            >
              {datasets.map(d => (
                <option key={d.id || d.dataset_id} value={d.id || d.dataset_id}>
                  {d.name || d.original_filename} ({d.id || d.dataset_id})
                </option>
              ))}
            </select>
          )}

          {columns.length > 0 && (
            <select
              className="border rounded px-3 py-1.5 text-sm bg-background"
              value={targetCol}
              onChange={(e) => setTargetCol(e.target.value)}
            >
              {columns.map(c => (
                <option key={c} value={c}>Target: {c}</option>
              ))}
            </select>
          )}

          <Button onClick={handleRunTournament} disabled={running || !selectedDatasetId || !targetCol}>
            {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Trophy className="mr-2 h-4 w-4" />}
            Run Tournament
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-red-500/50 bg-red-500/5 p-4 text-red-600 font-medium flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          {error}
        </Card>
      )}

      {results && results.status === 'SUCCESS' && (
        <div className="grid md:grid-cols-3 gap-6">
          {/* Selected Model Highlight */}
          <div className="md:col-span-1">
            <Card className="border-primary/50 bg-primary/5 h-full flex flex-col justify-between">
              <div>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-primary">
                    <Trophy className="h-5 w-5" /> Champion Model
                  </CardTitle>
                  <CardDescription>
                    {results.task_type === 'REGRESSION' ? 'Pareto-optimal model for regression' : 'Pareto-optimal model with highest F1 score'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="text-2xl font-bold">{selectedModel?.model_name}</p>
                    <div className="flex gap-2 mt-2">
                      <Badge variant="outline" className="bg-background border-emerald-500 text-emerald-600">
                        <CheckCircle className="h-3 w-3 mr-1" /> Pareto Optimal
                      </Badge>
                      <Badge variant="secondary">
                        {results.task_type || 'CLASSIFICATION'}
                      </Badge>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 text-sm pt-2 border-t">
                    {results.task_type === 'REGRESSION' ? (
                      <>
                        <div><span className="text-muted-foreground">R² Score:</span> <span className="font-mono font-medium">{selectedModel?.metrics?.r2?.toFixed(4)}</span></div>
                        <div><span className="text-muted-foreground">RMSE:</span> <span className="font-mono font-medium">{selectedModel?.metrics?.rmse?.toFixed(2)}</span></div>
                        <div><span className="text-muted-foreground">MAE:</span> <span className="font-mono font-medium">{selectedModel?.metrics?.mae?.toFixed(2)}</span></div>
                        <div><span className="text-muted-foreground">Size:</span> <span className="font-mono text-xs">{selectedModel?.metrics?.model_size_mb?.toFixed(2)}MB</span></div>
                      </>
                    ) : (
                      <>
                        <div><span className="text-muted-foreground">Accuracy:</span> <span className="font-mono font-medium">{((selectedModel?.metrics?.accuracy || 0) * 100).toFixed(1)}%</span></div>
                        <div><span className="text-muted-foreground">F1 Score:</span> <span className="font-mono font-medium">{((selectedModel?.metrics?.f1 || 0) * 100).toFixed(1)}%</span></div>
                        <div><span className="text-muted-foreground">Precision:</span> <span className="font-mono font-medium">{((selectedModel?.metrics?.precision || 0) * 100).toFixed(1)}%</span></div>
                        <div><span className="text-muted-foreground">Recall:</span> <span className="font-mono font-medium">{((selectedModel?.metrics?.recall || 0) * 100).toFixed(1)}%</span></div>
                      </>
                    )}
                    <div><span className="text-muted-foreground">Train Time:</span> <span className="font-mono text-xs">{selectedModel?.metrics?.training_time_s?.toFixed(3)}s</span></div>
                    <div><span className="text-muted-foreground">Latency:</span> <span className="font-mono text-xs">{selectedModel?.metrics?.inference_latency_ms?.toFixed(2)}ms</span></div>
                  </div>
                </CardContent>
              </div>
            </Card>
          </div>

          {/* Tournament Table */}
          <div className="md:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><BarChart3 className="h-5 w-5" /> Evaluated Candidates ({results.model_candidates?.length || 0})</CardTitle>
                <CardDescription>Task: {results.task_type} • Validation: {results.validation_strategy}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                      <tr>
                        <th className="px-3 py-3">Model</th>
                        {results.task_type === 'REGRESSION' ? (
                          <>
                            <th className="px-3 py-3">R² Score</th>
                            <th className="px-3 py-3">RMSE</th>
                            <th className="px-3 py-3">MAE</th>
                          </>
                        ) : (
                          <>
                            <th className="px-3 py-3">Accuracy</th>
                            <th className="px-3 py-3">F1</th>
                            <th className="px-3 py-3">Precision</th>
                          </>
                        )}
                        <th className="px-3 py-3">Latency</th>
                        <th className="px-3 py-3">Pareto</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {results.model_candidates?.map((m: any, idx: number) => (
                        <tr key={idx} className={m.model_name === selectedModel?.model_name ? 'bg-primary/5 font-semibold' : ''}>
                          <td className="px-3 py-3 font-medium">{m.model_name}</td>
                          {results.task_type === 'REGRESSION' ? (
                            <>
                              <td className="px-3 py-3 font-mono">{m.metrics?.r2?.toFixed(4)}</td>
                              <td className="px-3 py-3 font-mono">{m.metrics?.rmse?.toFixed(2)}</td>
                              <td className="px-3 py-3 font-mono">{m.metrics?.mae?.toFixed(2)}</td>
                            </>
                          ) : (
                            <>
                              <td className="px-3 py-3 font-mono">{((m.metrics?.accuracy || 0) * 100).toFixed(1)}%</td>
                              <td className="px-3 py-3 font-mono">{((m.metrics?.f1 || 0) * 100).toFixed(1)}%</td>
                              <td className="px-3 py-3 font-mono">{((m.metrics?.precision || 0) * 100).toFixed(1)}%</td>
                            </>
                          )}
                          <td className="px-3 py-3 font-mono text-xs">{m.metrics?.inference_latency_ms?.toFixed(2)}ms</td>
                          <td className="px-3 py-3">
                            {m.is_pareto_optimal ? (
                              <Badge variant="outline" className="text-xs border-emerald-500 text-emerald-600">Yes</Badge>
                            ) : (
                              <Badge variant="secondary" className="text-xs">No</Badge>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
