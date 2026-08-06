import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

const PLANS = [
  {
    name: "Starter",
    price: "$0",
    period: "/month",
    description: "For individual researchers evaluating the platform.",
    features: [
      "25 verified queries / month",
      "Source-grounded answers",
      "Hallucination scoring",
      "Markdown export",
    ],
    cta: "Start free",
    href: "/register",
  },
  {
    name: "Pro",
    price: "$49",
    period: "/month",
    description: "For lawyers and research teams with ongoing caseloads.",
    features: [
      "Unlimited queries",
      "Public share links",
      "Custom corpus ingestion",
      "Priority processing",
      "Evaluation dashboard",
    ],
    cta: "Start Pro",
    href: "/register",
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For firms needing compliance, SSO, and dedicated infrastructure.",
    features: [
      "Self-hosted deployment",
      "SSO / SAML",
      "Dedicated Qdrant cluster",
      "SLA & support",
      "Admin & audit controls",
    ],
    cta: "Contact sales",
    href: "/about",
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Simple, transparent pricing</h1>
        <p className="mt-2 text-muted-foreground">
          Start free. Upgrade when your research volume grows.
        </p>
      </div>

      <div className="mt-10 grid gap-6 md:grid-cols-3">
        {PLANS.map((plan) => (
          <Card key={plan.name} className={plan.featured ? "border-primary shadow-lg" : undefined}>
            <CardHeader>
              <CardTitle className="text-lg">{plan.name}</CardTitle>
              <div className="mt-2">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-muted-foreground">{plan.period}</span>
              </div>
              <CardDescription>{plan.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    {feature}
                  </li>
                ))}
              </ul>
            </CardContent>
            <CardFooter>
              <Button asChild variant={plan.featured ? "default" : "outline"} className="w-full">
                <Link href={plan.href}>{plan.cta}</Link>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
}
