import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import SemanticBreakpoint from '@/components/SemanticBreakpoint'
import { CheckCircle, Clock, PlayCircle, XCircle, AlertTriangle, UserCheck } from 'lucide-react'

const PIPELINE = [
  { id: 'ingest', name: 'INGEST', state: 'PASSED' },
  { id: 'profile', name: 'PROFILE', state: 'PASSED' },
  { id: 'semantic', name: 'SEMANTIC', state: 'HUMAN_REVIEW' },
  { id: 'analyst', name: 'ANALYST', state: 'WAITING' },
  { id: 'scientist', name: 'SCIENTIST', state: 'WAITING' },
  { id: 'verification', name: 'VERIFICATION', state: 'WAITING' },
  { id: 'engineer', name: 'ML ENGINEER', state: 'WAITING' },
]

export default function AgentExecutionCenter() {
  const [selectedAgent, setSelectedAgent] = useState('semantic')
  const [pipelineState, setPipelineState] = useState(PIPELINE)

  const handleResolve = () => {
    // Update states after HITL resolution
    const newPipeline = pipelineState.map(p => {
      if (p.id === 'semantic') return { ...p, state: 'PASSED' }
      if (p.id === 'analyst') return { ...p, state: 'RUNNING' }
      return p
    })
    setPipelineState(newPipeline)
    setSelectedAgent('analyst')
  }

  const getStateIcon = (state: string) => {
    switch(state) {
      case 'PASSED': return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'RUNNING': return <PlayCircle className="h-5 w-5 text-blue-500 animate-pulse" />
      case 'FAILED': return <XCircle className="h-5 w-5 text-destructive" />
      case 'BLOCKED': return <AlertTriangle className="h-5 w-5 text-orange-500" />
      case 'HUMAN_REVIEW': return <UserCheck className="h-5 w-5 text-purple-500" />
      default: return <Clock className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getAgentDetails = (id: string) => {
    if (id === 'semantic') {
      return {
        purpose: 'Resolve data ambiguity and build graph',
        status: pipelineState.find(p => p.id === id)?.state || 'WAITING',
        startTime: '10:42:01 AM',
        endTime: '--',
        inputs: ['customers.csv', 'Profiling metadata'],
        outputs: ['Knowledge Graph Nodes'],
        evidence: ['Found ambiguity in "status" column requiring human intervention.'],
        errors: []
      }
    }
    return {
      purpose: 'Execution stage: ' + id,
      status: pipelineState.find(p => p.id === id)?.state || 'WAITING',
      startTime: '--',
      endTime: '--',
      inputs: [],
      outputs: [],
      evidence: [],
      errors: []
    }
  }

  const details = getAgentDetails(selectedAgent)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Agent Execution Center</h2>
        <p className="text-muted-foreground">Monitor and interact with autonomous agents.</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Pipeline Visualizer */}
        <div className="lg:w-1/3">
          <Card>
            <CardHeader>
              <CardTitle>Execution Pipeline</CardTitle>
              <CardDescription>Live backend execution graph.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative border-l-2 border-muted ml-3 space-y-6">
                {pipelineState.map((node) => (
                  <div 
                    key={node.id} 
                    className={`relative flex items-center gap-4 pl-6 cursor-pointer group ${selectedAgent === node.id ? 'font-bold' : ''}`}
                    onClick={() => setSelectedAgent(node.id)}
                  >
                    <div className="absolute -left-[11px] bg-background">
                      {getStateIcon(node.state)}
                    </div>
                    <div className="flex-1">
                      <p className={`text-sm ${selectedAgent === node.id ? 'text-primary' : 'text-foreground group-hover:text-primary'}`}>
                        {node.name}
                      </p>
                      <p className="text-xs text-muted-foreground">{node.state.replace(/_/g, ' ')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Agent Details Pane */}
        <div className="lg:w-2/3 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="uppercase tracking-wide">{selectedAgent} Agent</CardTitle>
                <span className="text-xs font-mono px-2 py-1 bg-muted rounded">Status: {details.status}</span>
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="details">
                <TabsList className="mb-4">
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="io">I/O & Evidence</TabsTrigger>
                </TabsList>
                
                <TabsContent value="details" className="space-y-4">
                  <div>
                    <span className="text-xs text-muted-foreground uppercase">Purpose</span>
                    <p className="font-medium">{details.purpose}</p>
                  </div>
                  <div className="flex gap-8">
                    <div>
                      <span className="text-xs text-muted-foreground uppercase">Start Time</span>
                      <p className="font-medium font-mono">{details.startTime}</p>
                    </div>
                    <div>
                      <span className="text-xs text-muted-foreground uppercase">End Time</span>
                      <p className="font-medium font-mono">{details.endTime}</p>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="io" className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="border rounded p-4">
                      <span className="text-xs text-muted-foreground uppercase">Inputs</span>
                      <ul className="list-disc list-inside mt-2 text-sm">
                        {details.inputs.map((v,i) => <li key={i}>{v}</li>)}
                        {details.inputs.length === 0 && <span className="text-muted-foreground">None yet</span>}
                      </ul>
                    </div>
                    <div className="border rounded p-4">
                      <span className="text-xs text-muted-foreground uppercase">Outputs</span>
                      <ul className="list-disc list-inside mt-2 text-sm">
                        {details.outputs.map((v,i) => <li key={i}>{v}</li>)}
                        {details.outputs.length === 0 && <span className="text-muted-foreground">None yet</span>}
                      </ul>
                    </div>
                  </div>
                  <div>
                    <span className="text-xs text-muted-foreground uppercase">Evidence / Logs</span>
                    <div className="bg-muted p-3 mt-2 rounded font-mono text-xs overflow-auto h-32">
                      {details.evidence.map((v,i) => <div key={i}>&gt; {v}</div>)}
                      {details.evidence.length === 0 && <span className="text-muted-foreground">No events recorded.</span>}
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Render Breakpoint UI if status is HUMAN_REVIEW */}
          {details.status === 'HUMAN_REVIEW' && (
            <SemanticBreakpoint onResolve={handleResolve} />
          )}
        </div>
      </div>
    </div>
  )
}
