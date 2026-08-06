import { Scale, Target, ShieldCheck, Users } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const VALUES = [
  {
    icon: ShieldCheck,
    title: "Trust through verification",
    body: "We measure hallucination risk explicitly and surface it to users instead of hiding it. Every claim gets scored against its sources.",
  },
  {
    icon: Target,
    title: "Grounding first",
    body: "Retrieval-augmented generation is only trustworthy if the answer cites what it actually used. We enforce citation-to-source traceability.",
  },
  {
    icon: Scale,
    title: "Legal rigor",
    body: "Built with input from practitioners who know that an unverified legal claim can be worse than no claim at all.",
  },
  {
    icon: Users,
    title: "Open collaboration",
    body: "Share conversations read-only, export them, and let colleagues audit the underlying sources for themselves.",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center gap-2">
        <Scale className="h-6 w-6 text-primary" />
        <h1 className="text-3xl font-bold">About Legisight</h1>
      </div>
      <p className="mt-4 leading-relaxed text-muted-foreground">
        Legisight is a legal AI research platform that treats hallucination as a first-class
        engineering problem. Instead of simply generating answers from a language model, every
        response is anchored to retrieved passages, each citation is verified against its source,
        and a dedicated hallucination scorer reports residual risk.
      </p>
      <p className="mt-3 leading-relaxed text-muted-foreground">
        The stack is a retrieval-augmented generation pipeline — semantic and lexical retrieval
        over a Qdrant vector index, a grounded generation step, and a verification layer that
        computes citation overlap and confidence metrics on every assistant message.
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        {VALUES.map((value) => (
          <Card key={value.title}>
            <CardHeader>
              <value.icon className="h-8 w-8 text-primary" />
              <CardTitle className="text-lg">{value.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="leading-relaxed">{value.body}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
