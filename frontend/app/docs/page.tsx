import { BookOpen, MessageSquare, Search, Upload, ShieldCheck, Share2, Activity } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const SECTIONS = [
  {
    icon: MessageSquare,
    title: "Asking questions",
    body: "Start a chat on the Chat page. Answers stream in with inline citation markers that reference the sources panel below each message. Ask follow-up questions to refine the research thread.",
  },
  {
    icon: Search,
    title: "Source search",
    body: "The Search page runs semantic + lexical hybrid search over the corpus without generating an answer, so you can browse exact passages and their metadata (doc type, jurisdiction, year).",
  },
  {
    icon: Upload,
    title: "Ingesting documents",
    body: "Queue an ingestion job over a server-side directory of raw documents (PDF, TXT, MD, DOCX, HTML). Jobs chunk, embed, and upsert vectors. Use Rebuild index to (re)create the vector collection.",
  },
  {
    icon: ShieldCheck,
    title: "Understanding the safety metrics",
    body: "Every assistant answer is scored three ways: Hallucination check (risk of unsupported statements), Verification (each citation compared against its source passage for overlap), and Answer quality (faithfulness, answer relevance, context precision, context recall).",
  },
  {
    icon: Share2,
    title: "Sharing research",
    body: "Export any conversation as markdown, or generate a public read-only share link (slug) that anyone with the URL can view without an account. Revoke the link at any time.",
  },
  {
    icon: Activity,
    title: "Evaluation",
    body: "The Evaluation page aggregates quality and confidence scores across your recent conversations so you can gauge how the system is performing on your use cases.",
  },
];

export default function DocsPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <div className="flex items-center gap-2">
        <BookOpen className="h-6 w-6 text-primary" />
        <h1 className="text-3xl font-bold">Documentation</h1>
      </div>
      <p className="mt-2 text-muted-foreground">
        Everything you need to use Legisight for verified legal research.
      </p>

      <div className="mt-10 space-y-6">
        {SECTIONS.map((section) => (
          <Card key={section.title}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <section.icon className="h-5 w-5 text-primary" />
                {section.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-sm leading-relaxed">{section.body}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="mt-10 border-primary/30 bg-primary/5">
        <CardHeader>
          <CardTitle className="text-base">Important disclaimer</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Legisight reduces hallucination risk but does not eliminate it. Always verify
            high-stakes conclusions with the cited primary sources and consult a qualified
            attorney. Legisight does not provide legal advice.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
