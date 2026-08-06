import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  FileSearch,
  ShieldAlert,
  Sparkles,
  Layers,
  Lock,
  Gauge,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: BadgeCheck,
    title: "Every claim verified",
    description:
      "Each answer is checked against the cited primary sources, with an overlap score for every citation.",
  },
  {
    icon: ShieldAlert,
    title: "Hallucination alerts",
    description:
      "A dedicated hallucination-scoring engine flags low- and medium-confidence statements before you rely on them.",
  },
  {
    icon: Layers,
    title: "Multi-metric quality",
    description:
      "Faithfulness, answer relevance, and context recall are scored per response so you know how much to trust it.",
  },
  {
    icon: FileSearch,
    title: "Grounded retrieval",
    description:
      "Semantic search over statutes and case law returns only the passages your answer is actually built on.",
  },
  {
    icon: Gauge,
    title: "Transparent confidence",
    description:
      "A confidence meter shows exactly how strongly the model stands behind each part of its answer.",
  },
  {
    icon: Lock,
    title: "Share safely",
    description:
      "Export conversations as markdown or share a read-only public link with colleagues, never your account.",
  },
];

export default function HomePage() {
  return (
    <div className="relative">
      <section className="mx-auto max-w-5xl px-6 pb-20 pt-16 text-center sm:pt-24">
        <div className="inline-flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1 text-xs text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          Verified, source-grounded legal research
        </div>
        <h1 className="mt-6 text-4xl font-bold tracking-tight sm:text-6xl">
          Legal research that shows its work.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          Legisight answers legal questions with primary-source citations, verifies each claim
          against those sources, and surfaces hallucination risk before you trust it.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link href="/register">
              Start researching <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/docs">Read the docs</Link>
          </Button>
        </div>
      </section>

      <section className="border-t bg-muted/30 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-center text-2xl font-semibold sm:text-3xl">
            Built for trust, not just answers
          </h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <Card key={feature.title}>
                <CardHeader>
                  <feature.icon className="h-8 w-8 text-primary" />
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="leading-relaxed">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16 text-center">
        <h2 className="text-2xl font-semibold sm:text-3xl">How it works</h2>
        <div className="mt-10 grid gap-8 text-left sm:grid-cols-3">
          {[
            {
              step: "1",
              title: "Ask",
              body: "Pose a legal question in plain language. The system retrieves the most relevant statutes and case law.",
            },
            {
              step: "2",
              title: "Generate with citations",
              body: "The model answers with inline citations that map back to the exact retrieved passages.",
            },
            {
              step: "3",
              title: "Verify",
              body: "Every citation is cross-checked against its source and scored. Risky statements get flagged.",
            },
          ].map((item) => (
            <div key={item.step} className="relative rounded-lg border p-6">
              <span className="absolute -top-4 left-6 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                {item.step}
              </span>
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{item.body}</p>
            </div>
          ))}
        </div>
        <div className="mt-12">
          <Button asChild size="lg">
            <Link href="/register">Try Legisight free</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
