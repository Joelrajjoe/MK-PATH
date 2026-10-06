import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertCircle, CheckCircle, Edit2 } from 'lucide-react'

export default function KnowledgeUI() {
  const [goal, setGoal] = useState('Predict customer churn.')
  const [isEditingGoal, setIsEditingGoal] = useState(false)

  const concepts = [
    { name: 'customer_id', source: 'deterministic', definition: 'Unique identifier for a customer', confidence: 1.0, status: 'ready' },
    { name: 'status', source: 'llm_proposed', definition: 'Current account status', confidence: 0.65, status: 'needs_review' }
  ]

  return (
    <div className="space-y-8">
      {/* 1. Business Goal */}
      <Card>
        <CardHeader>
          <CardTitle>1. Business Goal</CardTitle>
          <CardDescription>The primary objective for this workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          {isEditingGoal ? (
            <div className="flex gap-2">
              <Input value={goal} onChange={e => setGoal(e.target.value)} />
              <Button onClick={() => setIsEditingGoal(false)}>Save</Button>
            </div>
          ) : (
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border">
              <p className="text-lg font-medium">"{goal}"</p>
              <Button variant="ghost" size="icon" onClick={() => setIsEditingGoal(true)}>
                <Edit2 className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 7. Ambiguities */}
      <Card className="border-orange-500/50 bg-orange-500/5">
        <CardHeader>
          <CardTitle className="text-orange-600 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" /> 7. AMBIGUITY DETECTED
          </CardTitle>
          <CardDescription>The semantic layer requires human clarification to proceed.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <Label className="text-orange-600/80">Column</Label>
              <p className="font-medium text-lg">status</p>
            </div>
            
            <div>
              <Label className="text-orange-600/80">Evidence (from backend profiling)</Label>
              <div className="mt-1 p-3 bg-background rounded border text-sm font-mono">
                Distinct values: [1, 2, 3, 4]
              </div>
            </div>

            <div>
              <Label className="text-orange-600/80">Possible interpretations</Label>
              <ul className="mt-1 list-disc list-inside text-sm">
                <li>Cancelled</li>
                <li>Test Order</li>
                <li>Fraud Hold</li>
              </ul>
            </div>

            <div className="flex gap-2 pt-2">
              <Button variant="default" className="bg-orange-600 hover:bg-orange-700">Resolve</Button>
              <Button variant="outline">Review</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. Dataset Concepts */}
      <Card>
        <CardHeader>
          <CardTitle>2. Dataset Concepts</CardTitle>
          <CardDescription>Semantic mapping of dataset columns.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                <tr>
                  <th className="px-4 py-3">Concept</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Definition</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {concepts.map((c, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3 font-medium">{c.name}</td>
                    <td className="px-4 py-3 text-xs font-mono bg-muted/30">{c.source}</td>
                    <td className="px-4 py-3">{c.definition}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-secondary rounded-full">
                          <div className={`h-2 rounded-full ${c.confidence >= 0.8 ? 'bg-green-500' : 'bg-orange-500'}`} style={{ width: `${c.confidence * 100}%` }}></div>
                        </div>
                        <span className="text-xs">{c.confidence}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {c.status === 'ready' ? (
                        <span className="flex items-center gap-1 text-green-600 text-xs"><CheckCircle className="h-3 w-3" /> Ready</span>
                      ) : (
                        <span className="flex items-center gap-1 text-orange-600 text-xs"><AlertCircle className="h-3 w-3" /> Needs Review</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* 3-6. Knowledge Graph Preparation placeholders */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card><CardHeader><CardTitle className="text-base">3. Business Terms</CardTitle></CardHeader></Card>
        <Card><CardHeader><CardTitle className="text-base">4. Metrics</CardTitle></CardHeader></Card>
        <Card><CardHeader><CardTitle className="text-base">5. Dimensions</CardTitle></CardHeader></Card>
        <Card><CardHeader><CardTitle className="text-base">6. Relationships</CardTitle></CardHeader></Card>
      </div>
    </div>
  )
}
