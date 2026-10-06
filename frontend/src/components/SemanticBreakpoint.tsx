import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { AlertCircle, CheckCircle, RefreshCcw, Hand } from 'lucide-react'

export type HitlState = 'WAITING_FOR_HUMAN' | 'ANSWER_SUBMITTED' | 'RESUMING' | 'RESUMED' | 'FAILED'

interface HitlProps {
  initialState?: HitlState;
  onResolve?: () => void;
}

export default function SemanticBreakpoint({ initialState = 'WAITING_FOR_HUMAN', onResolve }: HitlProps) {
  const [state, setState] = useState<HitlState>(initialState)
  const [selectedOption, setSelectedOption] = useState<string>('')

  const handleConfirm = () => {
    setState('ANSWER_SUBMITTED')
    setTimeout(() => setState('RESUMING'), 1000)
    setTimeout(() => {
      setState('RESUMED')
      if (onResolve) onResolve()
    }, 2500)
  }

  if (state === 'RESUMED') return null

  return (
    <Card className="border-blue-500/50 shadow-lg bg-blue-500/5 max-w-2xl mx-auto my-6">
      <CardHeader className="pb-3 border-b border-blue-500/20 bg-blue-500/10">
        <div className="flex items-center justify-between">
          <CardTitle className="text-blue-700 flex items-center gap-2">
            <Hand className="h-5 w-5" /> MK-PATH NEEDS YOUR DECISION
          </CardTitle>
          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full uppercase tracking-wider">
            {state.replace(/_/g, ' ')}
          </span>
        </div>
        <CardDescription className="text-blue-900/70 font-medium">
          Workflow paused • Agent: Semantic Resolver • Reason: Business ambiguity
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-6 space-y-6">
        {state === 'WAITING_FOR_HUMAN' ? (
          <>
            <div>
              <p className="text-lg font-medium">We found an ambiguous business definition.</p>
              <div className="mt-4 p-4 border rounded bg-background">
                <Label className="text-muted-foreground uppercase text-xs">Column</Label>
                <p className="font-mono text-base mb-4">status</p>

                <Label className="text-muted-foreground uppercase text-xs">Evidence</Label>
                <ul className="list-disc list-inside text-sm mt-1 mb-4">
                  <li>98.2% have $0 transaction value</li>
                  <li>96.7% use internal email domains</li>
                </ul>

                <Label className="text-foreground font-medium text-base">Question:</Label>
                <p className="text-lg font-semibold mt-1">What does status=4 represent?</p>
              </div>
            </div>

            <div>
              <Label className="text-muted-foreground uppercase text-xs">Possible meaning</Label>
              <div className="mt-2 space-y-2">
                {['Cancelled Order', 'Test Order', 'Fraud Hold', 'Other'].map((opt) => (
                  <label key={opt} className={`flex items-center gap-3 p-3 border rounded cursor-pointer transition-colors ${selectedOption === opt ? 'bg-blue-50 border-blue-400' : 'hover:bg-muted'}`}>
                    <input 
                      type="radio" 
                      name="interpretation" 
                      value={opt}
                      checked={selectedOption === opt}
                      onChange={() => setSelectedOption(opt)}
                      className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500" 
                    />
                    <span className="font-medium">{opt}</span>
                  </label>
                ))}
              </div>
            </div>
          </>
        ) : state === 'ANSWER_SUBMITTED' ? (
          <div className="flex flex-col items-center justify-center py-8 text-center space-y-4">
            <CheckCircle className="h-12 w-12 text-green-500" />
            <h3 className="text-xl font-medium text-green-700">Decision saved ✓</h3>
          </div>
        ) : state === 'RESUMING' ? (
          <div className="flex flex-col items-center justify-center py-8 text-center space-y-4">
            <RefreshCcw className="h-12 w-12 text-blue-500 animate-spin" />
            <h3 className="text-xl font-medium text-blue-700">Workflow resuming...</h3>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center space-y-4">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <h3 className="text-xl font-medium text-destructive">Failed to resume workflow</h3>
          </div>
        )}
      </CardContent>

      {state === 'WAITING_FOR_HUMAN' && (
        <CardFooter className="flex justify-between bg-muted/20 border-t p-4">
          <Button variant="outline" className="text-destructive hover:bg-destructive/10">Reject</Button>
          <div className="flex gap-2">
            <Button variant="outline">Provide Custom Definition</Button>
            <Button disabled={!selectedOption} onClick={handleConfirm} className="bg-blue-600 hover:bg-blue-700">Confirm Decision</Button>
          </div>
        </CardFooter>
      )}
    </Card>
  )
}
