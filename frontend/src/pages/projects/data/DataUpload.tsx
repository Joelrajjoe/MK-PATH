import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { UploadCloud, FileType, CheckCircle, AlertCircle, Database } from 'lucide-react'

export default function DataUpload({ projectId }: { projectId: string }) {
  const navigate = useNavigate()
  const [dragActive, setDragActive] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [status, setStatus] = useState<string>('IDLE')
  const [progress, setProgress] = useState(0)
  const [dataset, setDataset] = useState<any>(null)
  const [existingDatasets, setExistingDatasets] = useState<any[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  
  const inputRef = useRef<HTMLInputElement>(null)

  const fetchExisting = () => {
    if (projectId) {
      api.datasets.list(projectId).then(ds => {
        setExistingDatasets(ds)
      }).catch(console.error)
    }
  }

  useEffect(() => {
    fetchExisting()
  }, [projectId, status])

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = async (file: File) => {
    // Validate extension
    const ext = file.name.split('.').pop()?.toLowerCase()
    const allowed = ['csv', 'xlsx', 'xls', 'json', 'parquet', 'sql', 'zip']
    if (!ext || !allowed.includes(ext)) {
      setErrorMsg('Unsupported format. Please upload CSV, Excel, JSON, Parquet, SQL, or ZIP.')
      setStatus('FAILED')
      return
    }

    setFiles([file])
    setStatus('UPLOADING')
    setErrorMsg(null)
    setProgress(0)

    try {
      const result = await api.datasets.upload(projectId, file, (p) => {
        setProgress(p)
      })
      setStatus('COMPLETED')
      setDataset(result)
      fetchExisting()
    } catch (err: any) {
      setErrorMsg(err.message || 'Upload failed. Please try again.')
      setStatus('FAILED')
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Upload Data</CardTitle>
          <CardDescription>Supported formats: CSV · Excel · JSON · Parquet · SQL · ZIP</CardDescription>
        </CardHeader>
        <CardContent>
          {status === 'IDLE' || status === 'FAILED' ? (
            <div
              className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-colors ${
                dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 bg-muted/50'
              } ${status === 'FAILED' ? 'border-destructive/50 bg-destructive/5' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                accept=".csv,.xlsx,.xls,.json,.parquet,.sql,.zip"
                onChange={handleChange}
              />
              <UploadCloud className="mb-4 h-10 w-10 text-muted-foreground" />
              <div className="mb-2 flex items-center justify-center text-sm font-medium">
                <span>Drop your data here</span>
              </div>
              <p className="text-xs text-muted-foreground">or browse files</p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => inputRef.current?.click()}
              >
                Select File
              </Button>
              
              {status === 'FAILED' && errorMsg && (
                <div className="mt-4 flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  {errorMsg}
                </div>
              )}
            </div>
          ) : status === 'COMPLETED' && dataset ? (
            <div className="rounded-lg border p-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-500/10 text-green-500">
                  <CheckCircle className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-medium text-lg">Upload Successful</h3>
                  <p className="text-sm text-muted-foreground">
                    Processed {dataset.datasets?.length || 1} dataset(s)
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {(dataset.datasets || [dataset]).map((ds: any) => (
                  <div key={ds.dataset_id || ds.id} className="rounded border p-4 bg-muted/20">
                    <h4 className="font-medium">{ds.original_filename || ds.name}</h4>
                    <p className="text-sm text-muted-foreground mb-3">
                      Format: {(ds.source_format || ds.format || '').toUpperCase()} • Rows: {ds.row_count || ds.rowCount} • Columns: {ds.column_count || ds.columnCount}
                    </p>
                    <div className="flex gap-4">
                      <Button variant="default" size="sm" onClick={() => navigate(`/projects/${projectId}/data/${ds.dataset_id || ds.id}`)}>
                        <Database className="mr-2 h-4 w-4" /> View Dataset
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => setStatus('IDLE')}>
                        Upload Another
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="rounded-lg border p-6 text-center">
              <div className="mb-4 flex justify-center">
                <FileType className="h-10 w-10 animate-pulse text-primary" />
              </div>
              <h3 className="font-medium mb-2">Processing {files[0]?.name}</h3>
              <p className="text-sm text-muted-foreground mb-4">Status: {status}</p>
              <div className="w-full bg-secondary rounded-full h-2.5">
                <div className="bg-primary h-2.5 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Existing Uploaded Datasets List */}
      {existingDatasets.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" /> Uploaded Datasets ({existingDatasets.length})
            </CardTitle>
            <CardDescription>Select a dataset to explore schema, quality profile, and rows.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {existingDatasets.map((ds: any) => (
              <div key={ds.id || ds.dataset_id} className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-lg border bg-muted/20 hover:bg-muted/40 transition-colors gap-4">
                <div className="space-y-1">
                  <h4 className="font-semibold text-base flex items-center gap-2">
                    {ds.name || ds.original_filename || ds.table_name || 'Dataset'}
                  </h4>
                  <p className="text-xs text-muted-foreground font-mono">
                    ID: {ds.id || ds.dataset_id} • Format: {(ds.source_format || ds.format || 'csv').toUpperCase()} • Rows: {ds.row_count ?? ds.rowCount ?? 0} • Columns: {ds.column_count ?? ds.columnCount ?? 0}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => navigate(`/projects/${projectId}/data/${ds.id || ds.dataset_id}`)}>
                    <Database className="mr-2 h-4 w-4" /> Explore Dataset
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
