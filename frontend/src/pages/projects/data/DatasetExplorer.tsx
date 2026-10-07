import { useState, useEffect } from 'react'
import { useParams, Link, useLocation } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, Play, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { api, type Dataset } from '@/lib/api'

export default function DatasetExplorer({ datasetId: propDatasetId }: { datasetId?: string } = {}) {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()
  const pathParts = location.pathname.split('/')
  const datasetId = propDatasetId || pathParts[4] || ''
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [schemaData, setSchemaData] = useState<any>(null)
  const [previewData, setPreviewData] = useState<any>(null)
  const [qualityData, setQualityData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [profiling, setProfiling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadAllData = async (dsId: string) => {
    setLoading(true)
    setError(null)
    try {
      const ds = await api.datasets.get(dsId)
      setDataset(ds)

      const [s, p, q] = await Promise.all([
        api.datasets.schema(dsId).catch(() => null),
        api.datasets.preview(dsId, 10).catch(() => null),
        api.datasets.quality(dsId).catch(() => null)
      ])

      setSchemaData(s)
      setPreviewData(p)
      setQualityData(q)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Failed to load dataset details.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (datasetId) {
      loadAllData(datasetId)
    }
  }, [datasetId])

  const handleRunProfile = async () => {
    if (!datasetId) return
    setProfiling(true)
    try {
      await api.datasets.profile(datasetId)
      await loadAllData(datasetId)
    } catch (err: any) {
      alert(err.message || 'Profiling failed')
    } finally {
      setProfiling(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !dataset) {
    return (
      <Card className="border-destructive/50 bg-destructive/5 p-6 text-destructive">
        <AlertCircle className="h-6 w-6 mb-2" />
        <h3 className="font-bold">Dataset Error</h3>
        <p className="text-sm">{error || 'Dataset not found.'}</p>
        <Button variant="outline" className="mt-4" asChild>
          <Link to={`/projects/${projectId}/data`}>Back to Datasets</Link>
        </Button>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link to={`/projects/${projectId}/data`}><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{dataset.name}</h2>
            <p className="text-sm text-muted-foreground">
              Format: {(dataset.format || dataset.source_format || '').toUpperCase()} • Rows: {dataset.rowCount ?? dataset.row_count ?? 0} • Cols: {dataset.columnCount ?? dataset.column_count ?? 0}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="default" onClick={handleRunProfile} disabled={profiling}>
            {profiling ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            Run Profile
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="flex-1 flex flex-col">
        <TabsList className="w-fit">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="schema">Schema</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="quality">Quality</TabsTrigger>
        </TabsList>

        <div className="mt-4">
          <TabsContent value="overview">
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Rows</CardTitle></CardHeader>
                <CardContent><div className="text-2xl font-bold">{dataset.rowCount ?? dataset.row_count ?? 0}</div></CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Columns</CardTitle></CardHeader>
                <CardContent><div className="text-2xl font-bold">{dataset.columnCount ?? dataset.column_count ?? 0}</div></CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Quality Score</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-emerald-600">
                    {dataset.qualityScore !== undefined ? `${dataset.qualityScore}/100` : 'Not Profiled'}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-medium">Status</CardTitle></CardHeader>
                <CardContent><div className="text-2xl font-bold uppercase">{dataset.status || 'COMPLETED'}</div></CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="schema">
            <Card>
              <CardHeader>
                <CardTitle>Dataset Schema</CardTitle>
                <CardDescription>Real extracted column metadata</CardDescription>
              </CardHeader>
              <CardContent>
                {!schemaData || !schemaData.columns || schemaData.columns.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No schema available.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                        <tr>
                          <th className="px-4 py-3">Column</th>
                          <th className="px-4 py-3">Type</th>
                          <th className="px-4 py-3">Nullable</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {schemaData.columns.map((c: any, idx: number) => (
                          <tr key={idx}>
                            <td className="px-4 py-3 font-medium">{c.name}</td>
                            <td className="px-4 py-3 font-mono text-xs">{c.type}</td>
                            <td className="px-4 py-3">{c.nullable ? 'Yes' : 'No'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="preview">
            <Card>
              <CardHeader>
                <CardTitle>Data Preview</CardTitle>
                <CardDescription>Live query results from DuckDB</CardDescription>
              </CardHeader>
              <CardContent>
                {!previewData || !previewData.rows || previewData.rows.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No preview rows returned.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                        <tr>
                          {previewData.columns.map((colName: string, idx: number) => (
                            <th key={idx} className="px-4 py-3">{colName}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {previewData.rows.map((row: any, rIdx: number) => (
                          <tr key={rIdx}>
                            {previewData.columns.map((colName: string, cIdx: number) => (
                              <td key={cIdx} className="px-4 py-3 text-xs font-mono">{String(row[colName] ?? '')}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="quality">
            <Card>
              <CardHeader>
                <CardTitle>Data Quality Assessment</CardTitle>
                <CardDescription>Deterministic backend profiling report</CardDescription>
              </CardHeader>
              <CardContent>
                {!qualityData ? (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground text-sm mb-4">No quality report exists yet.</p>
                    <Button onClick={handleRunProfile} disabled={profiling}>Run Profile Now</Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center gap-4 p-4 border rounded-lg bg-emerald-500/10 border-emerald-500/20">
                      <CheckCircle className="h-6 w-6 text-emerald-500" />
                      <div>
                        <p className="font-bold text-lg">Quality Score: {qualityData.quality_score}/100 ({qualityData.quality_grade})</p>
                        <p className="text-xs text-muted-foreground">Engine: {qualityData.engine}</p>
                      </div>
                    </div>
                    {qualityData.issues && qualityData.issues.map((issue: any, i: number) => (
                      <div key={i} className="flex items-start gap-4 p-4 border rounded-lg">
                        <AlertCircle className="h-5 w-5 text-orange-500" />
                        <div>
                          <p className="font-semibold text-sm">{issue.message || JSON.stringify(issue)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
