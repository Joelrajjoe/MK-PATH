import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { api, type Project } from '@/lib/api'
import { Plus } from 'lucide-react'

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([])

  useEffect(() => {
    api.projects.list().then(setProjects)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Projects</h2>
          <p className="text-muted-foreground">Manage your transformation workspaces.</p>
        </div>
        <Button asChild>
          <Link to="/projects/new">
            <Plus className="mr-2 h-4 w-4" /> New Project
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {projects.length === 0 ? (
          <p className="text-muted-foreground">No projects found. Create one to get started.</p>
        ) : (
          projects.map(p => (
            <Card key={p.id} className="flex flex-col">
              <CardHeader>
                <CardTitle>{p.name}</CardTitle>
                <CardDescription>{p.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <div>Datasets: {p.datasetCount}</div>
                  <div>Models: {p.modelCount}</div>
                </div>
                <div className="mt-4">
                  <Button variant="outline" asChild className="w-full">
                    <Link to={`/projects/${p.id}`}>Open Workspace</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
