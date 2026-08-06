import Link from "next/link";
import { CheckCircle2, ShieldCheck, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function VerifyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-6 w-6 text-primary" />
        <h1 className="text-3xl font-bold">How we fight hallucinations</h1>
      </div>

      <div className="mt-8 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              1. Ground every answer
            </CardTitle>
            <CardDescription>
              No answer is generated from the model alone. Retrieval first pulls candidate passages
              from the legal corpus, and generation is constrained to those passages.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              2. Verify each citation
            </CardTitle>
            <CardDescription>
              Every inline citation is mapped back to the exact chunk it came from. The verification
              layer computes lexical overlap between the cited claim and the source passage, so you
              can see how faithfully the answer reflects its source.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              3. Score hallucination risk
            </CardTitle>
            <CardDescription>
              A dedicated hallucination scorer flags statements that are unsupported, contradictory,
              or over-generalized relative to the context, and assigns a low / medium / high risk
              verdict to every answer.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card className="border-warning/40 bg-warning/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg text-warning">
              <AlertTriangle className="h-5 w-5" />
              What this does not do
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Verification reduces risk; it cannot guarantee correctness. Citations can be accurate
              but incomplete, and the corpus itself may not be exhaustive. Always review the cited
              sources for consequential legal decisions.
            </p>
          </CardContent>
        </Card>

        <div className="text-center">
          <Button asChild size="lg">
            <Link href="/register">Try it yourself</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
