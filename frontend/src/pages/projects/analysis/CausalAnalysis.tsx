import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle, BrainCircuit } from 'lucide-react'

export default function CausalAnalysis() {
  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Causal Analysis</h2>
        <p className="text-muted-foreground">Understand the estimated treatment effects and underlying causal graph.</p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Causal Question</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 border rounded bg-muted/20">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">Treatment</span>
                  <p className="font-medium text-lg">Applied Discount Code</p>
                </div>
                <div className="p-3 border rounded bg-muted/20">
                  <span className="text-xs text-muted-foreground uppercase font-semibold">Outcome</span>
                  <p className="font-medium text-lg">Retained (1 Month)</p>
                </div>
              </div>
              <div className="p-3 border rounded bg-muted/20">
                <span className="text-xs text-muted-foreground uppercase font-semibold">Confounders Adjusted</span>
                <p className="text-sm mt-1">account_age, support_tickets, region, usage_frequency</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Estimated Treatment Effect</CardTitle>
              <CardDescription>Careful estimation of the causal impact, relying on backend assertions.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-8">
                <div>
                  <div className="text-4xl font-bold text-primary">+14.2%</div>
                  <p className="text-sm text-muted-foreground mt-1">Average Treatment Effect (ATE)</p>
                </div>
                <div className="h-12 w-px bg-border"></div>
                <div>
                  <div className="text-xl font-medium">[ +11.5% , +16.9% ]</div>
                  <p className="text-sm text-muted-foreground mt-1">95% Confidence Interval</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Causal Graph</CardTitle>
              <CardDescription>Backend-provided structural relationships.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 border rounded flex items-center justify-center bg-muted/10">
                {/* Real app would render a directed acyclic graph (DAG) here based on backend structure */}
                <div className="flex items-center gap-8 text-sm font-medium">
                  <div className="p-3 border rounded bg-background shadow-sm">Discount</div>
                  <span>→</span>
                  <div className="p-3 border rounded bg-background shadow-sm border-primary text-primary">Retention</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><BrainCircuit className="h-5 w-5" /> Refutation Tests</CardTitle>
              <CardDescription>Robustness checks against the causal model.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center p-2 border-b">
                <span className="text-sm font-medium">Placebo test</span>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="h-3 w-3 mr-1" /> PASS</Badge>
              </div>
              <div className="flex justify-between items-center p-2 border-b">
                <span className="text-sm font-medium">Random common cause</span>
                <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle className="h-3 w-3 mr-1" /> PASS</Badge>
              </div>
              <div className="flex justify-between items-center p-2 border-b">
                <span className="text-sm font-medium">Subset validation</span>
                <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200"><AlertCircle className="h-3 w-3 mr-1" /> WARNING</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Assumptions & Limitations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <div className="flex gap-2 items-start">
                <CheckCircle className="h-4 w-4 mt-0.5" />
                <p>Assumes no unobserved confounders (Unconfoundedness).</p>
              </div>
              <div className="flex gap-2 items-start">
                <AlertCircle className="h-4 w-4 mt-0.5" />
                <p>Subset validation warning indicates potential heterogeneity in effect across unmeasured segments.</p>
              </div>
              <div className="p-3 bg-muted/30 rounded border text-xs">
                <strong>Note:</strong> This is an estimated treatment effect, not a guaranteed causal effect. Interpret alongside domain expertise.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
