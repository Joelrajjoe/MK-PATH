import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { CheckCircle, BrainCircuit, BarChart, Database, ListFilter, Calendar, Settings2, Link as LinkIcon } from 'lucide-react'

export default function DataAnalystWorkspace() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [approved, setApproved] = useState(false)

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setSubmitted(true)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Data Analyst Workspace</h2>
        <p className="text-muted-foreground">Collaborate with the Data Analyst Agent to understand your data.</p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleAnalyze} className="flex gap-4">
            <Input 
              placeholder="What do you want to understand? (e.g., Analyze why customer churn increased)"
              value={query}
              onChange={e => setQuery(e.target.value)}
              className="text-lg py-6"
            />
            <Button type="submit" size="lg" className="px-8">Analyze</Button>
          </form>
        </CardContent>
      </Card>

      {submitted && (
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-1 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><BrainCircuit className="h-4 w-4" /> Context</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <span className="text-muted-foreground block mb-1">Business Goal</span>
                  <p className="font-medium">Predict customer churn</p>
                </div>
                <div>
                  <span className="text-muted-foreground block mb-1">Selected Dataset</span>
                  <p className="font-medium flex items-center gap-1"><Database className="h-3 w-3" /> customers.csv</p>
                </div>
                <div>
                  <span className="text-muted-foreground block mb-1">Semantic Context</span>
                  <p className="font-medium text-xs bg-muted p-2 rounded">
                    Mapped 12 columns to Churn metrics framework. Resolved "status" ambiguity.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-primary/20">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2"><Settings2 className="h-4 w-4" /> Analysis Plan</CardTitle>
                <CardDescription>Proposed by DA Agent</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex gap-2 items-start">
                  <BarChart className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div>
                    <span className="font-semibold block">Metrics</span>
                    <span className="text-muted-foreground">Churn Rate, LTV</span>
                  </div>
                </div>
                <div className="flex gap-2 items-start">
                  <ListFilter className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div>
                    <span className="font-semibold block">Dimensions</span>
                    <span className="text-muted-foreground">Region, Subscription Tier</span>
                  </div>
                </div>
                <div className="flex gap-2 items-start">
                  <Calendar className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div>
                    <span className="font-semibold block">Time Period</span>
                    <span className="text-muted-foreground">Trailing 12 months</span>
                  </div>
                </div>
                <div className="flex gap-2 items-start">
                  <LinkIcon className="h-4 w-4 mt-0.5 text-muted-foreground" />
                  <div>
                    <span className="font-semibold block">Comparisons</span>
                    <span className="text-muted-foreground">MoM Churn, Cohort analysis</span>
                  </div>
                </div>
              </CardContent>
              {!approved ? (
                <CardFooter>
                  <Button className="w-full" onClick={() => setApproved(true)}>Approve Plan</Button>
                </CardFooter>
              ) : (
                <CardFooter>
                  <div className="flex items-center gap-2 text-green-600 text-sm font-medium w-full justify-center">
                    <CheckCircle className="h-4 w-4" /> Plan Approved
                  </div>
                </CardFooter>
              )}
            </Card>
          </div>

          <div className="md:col-span-2 space-y-6">
            {!approved ? (
              <div className="h-full flex items-center justify-center border border-dashed rounded-lg text-muted-foreground p-12 text-center">
                Review and approve the analysis plan on the left to generate results.
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">Overall Churn Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">4.2%</div>
                      <p className="text-xs text-destructive mt-1">+0.8% vs last month</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">High-Risk Cohort</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-3xl font-bold">Tier 1</div>
                      <p className="text-xs text-muted-foreground mt-1">12% churn rate in segment</p>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle>Churn Trend by Segment</CardTitle>
                    <CardDescription>Trailing 12 months analysis</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64 bg-muted/30 rounded flex items-center justify-center text-muted-foreground border border-dashed">
                      [Plotly / Chart implementation here]
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Provenance & Evidence</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="p-3 border rounded text-sm bg-muted/20">
                      <div className="font-semibold mb-2 flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500" /> Result Verification
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                        <div><span className="font-medium text-foreground">Dataset:</span> customers.csv</div>
                        <div><span className="font-medium text-foreground">Run ID:</span> run_a9f8b2</div>
                        <div><span className="font-medium text-foreground">Columns:</span> status, created_at, tier</div>
                        <div><span className="font-medium text-foreground">Calc:</span> count(status='Cancelled') / count(*)</div>
                      </div>
                      <div className="mt-3">
                        <Button variant="link" className="p-0 h-auto text-xs">View underlying evidence & SQL →</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
