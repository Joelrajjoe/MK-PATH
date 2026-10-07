import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import ProjectOverview from './ProjectOverview'
import DataUpload from './data/DataUpload'
import DatasetExplorer from './data/DatasetExplorer'
import KnowledgeUI from './knowledge/KnowledgeUI'
import AgentExecutionCenter from './agents/AgentExecutionCenter'
import DataAnalystWorkspace from './analysis/DataAnalystWorkspace'
import TemporalLeakage from './verification/TemporalLeakage'
import CausalAnalysis from './analysis/CausalAnalysis'
import ModelTournament from './models/ModelTournament'
import VerificationCenter from './verification/VerificationCenter'
import HealingUI from './healing/HealingUI'
import ArtifactCenter from './artifacts/ArtifactCenter'
import AuditUI from './audit/AuditUI'

export default function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const location = useLocation()

  // Determine current tab from URL (e.g. /projects/123/data -> 'data')
  // The path starts with /projects/:id/ so split[3] is the tab, defaulting to 'overview'
  const pathParts = location.pathname.split('/')
  const activeTab = pathParts[3] || 'overview'

  return (
    <div className="flex h-full flex-col space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Project Workspace</h2>
        <p className="text-muted-foreground">ID: {projectId}</p>
      </div>

      <Tabs value={activeTab} onValueChange={(val) => navigate(`/projects/${projectId}/${val}`)} className="flex-1 flex flex-col">
        <TabsList className="w-fit flex-wrap">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="data">Data</TabsTrigger>
          <TabsTrigger value="knowledge">Knowledge</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="verification">Verification</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
          <TabsTrigger value="healing">Healing</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <div className="flex-1 mt-4">
          <TabsContent value="overview" className="h-full">
            <ProjectOverview
              projectId={projectId!}
              onNavigateTab={(tab) => navigate(`/projects/${projectId}/${tab}`)}
            />
          </TabsContent>

          <TabsContent value="data" className="h-full">
            {pathParts[4] ? <DatasetExplorer datasetId={pathParts[4]} /> : <DataUpload projectId={projectId!} />}
          </TabsContent>
          
          <TabsContent value="knowledge" className="h-full">
            <KnowledgeUI projectId={projectId} />
          </TabsContent>

          <TabsContent value="agents" className="h-full">
            <AgentExecutionCenter />
          </TabsContent>
          
          <TabsContent value="analysis" className="h-full">
            {pathParts[4] === 'causal' ? <CausalAnalysis /> : <DataAnalystWorkspace />}
          </TabsContent>

          <TabsContent value="verification" className="h-full">
            {pathParts[4] === 'leakage' ? <TemporalLeakage /> : <VerificationCenter />}
          </TabsContent>

          <TabsContent value="models" className="h-full">
            <ModelTournament />
          </TabsContent>

          <TabsContent value="healing" className="h-full">
            <HealingUI />
          </TabsContent>

          <TabsContent value="artifacts" className="h-full">
            <ArtifactCenter />
          </TabsContent>

          <TabsContent value="audit" className="h-full">
            <AuditUI />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
