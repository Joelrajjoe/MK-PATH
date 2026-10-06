import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, Wand2, ArrowRight, ShieldAlert, CheckCircle } from 'lucide-react'

export default function HealingUI() {
  const problems = [
    { id: 'p1', type: 'Missing Values', col: 'monthly_income', count: '12.3%', proposal: 'Median imputation by customer segment', risk: 'Medium', approved: false },
    { id: 'p2', type: 'Outliers', col: 'transaction_amount', count: '0.8%', proposal: 'Winsorization at 99th percentile', risk: 'Low', approved: true },
    { id: 'p3', type: 'Semantic Inconsistencies', col: 'status', count: '2.1%', proposal: 'Map "Cancelled" and "Void" to "churned"', risk: 'High', approved: false },
  ]

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Transformation & Healing</h2>
        <p className="text-muted-foreground">Review and approve automated data quality corrections.</p>
      </div>

      <div className="p-4 bg-muted/40 border rounded-lg flex items-start gap-4">
        <ShieldAlert className="h-5 w-5 text-muted-foreground mt-0.5" />
        <div>
          <h4 className="font-semibold text-sm">Original Dataset is Immutable</h4>
          <p className="text-sm text-muted-foreground">Healing operations strictly generate a <strong>Derived Dataset</strong>. Original data is never overwritten or modified.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Detected Problems & Proposals</CardTitle>
              <CardDescription>Review the healing proposals suggested by the data scientist agent.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {problems.map(p => (
                <div key={p.id} className="border rounded-lg p-4 bg-background shadow-sm flex flex-col gap-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-orange-500" />
                        <span className="font-bold">{p.type}</span>
                        <Badge variant="outline" className="font-mono text-[10px]">{p.col}</Badge>
                      </div>
                      <p className="text-sm mt-1 text-muted-foreground">Impacts {p.count} of rows.</p>
                    </div>
                    <Badge variant={p.approved ? 'default' : 'secondary'} className={p.approved ? 'bg-green-600' : ''}>
                      {p.approved ? 'Approved' : 'Needs Approval'}
                    </Badge>
                  </div>
                  
                  <div className="bg-muted/30 p-3 rounded text-sm border flex items-center justify-between">
                    <div>
                      <span className="text-xs uppercase text-muted-foreground font-semibold block mb-1">Proposal</span>
                      <p className="font-medium flex items-center gap-2"><Wand2 className="h-3 w-3 text-primary" /> {p.proposal}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-xs uppercase text-muted-foreground font-semibold block mb-1">Risk</span>
                      <p className={`font-semibold ${p.risk === 'High' ? 'text-destructive' : p.risk === 'Medium' ? 'text-orange-500' : 'text-green-600'}`}>{p.risk}</p>
                    </div>
                  </div>

                  {!p.approved && (
                    <div className="flex gap-2 justify-end">
                      <Button variant="ghost" size="sm">Review Details</Button>
                      <Button variant="outline" size="sm" className="text-destructive">Reject</Button>
                      <Button variant="default" size="sm">Approve</Button>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quality Before / After</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="text-center">
                  <p className="text-xs text-muted-foreground font-semibold uppercase">Before</p>
                  <p className="text-3xl font-bold text-destructive">68</p>
                  <p className="text-xs text-muted-foreground mt-1">Quality Score</p>
                </div>
                <ArrowRight className="h-6 w-6 text-muted-foreground" />
                <div className="text-center">
                  <p className="text-xs text-muted-foreground font-semibold uppercase">Projected</p>
                  <p className="text-3xl font-bold text-green-600">92</p>
                  <p className="text-xs text-muted-foreground mt-1">Quality Score</p>
                </div>
              </div>

              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Changed Rows</span>
                  <span className="font-medium font-mono">14.1%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Changed Columns</span>
                  <span className="font-medium font-mono">2 of 12</span>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button className="w-full bg-green-600 hover:bg-green-700" disabled>
                <CheckCircle className="h-4 w-4 mr-2" /> Execute Transformations
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  )
}
