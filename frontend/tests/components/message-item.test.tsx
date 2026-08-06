import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MessageItem } from "@/components/chat/message-item";
import type { Message } from "@/lib/types";

function renderMessage(message: Message) {
  return render(
    <TooltipProvider>
      <MessageItem message={message} />
    </TooltipProvider>,
  );
}

const USER_MESSAGE: Message = {
  id: "m1",
  role: "user",
  content: "What is negligence?",
  sources: [],
  citations: [],
  quality_score: 0,
  latency_ms: 0,
  tokens: 0,
  created_at: "2026-01-01T00:00:00Z",
};

const ASSISTANT_MESSAGE: Message = {
  id: "m2",
  role: "assistant",
  content: "**Negligence** requires four elements. [1]",
  sources: [
    {
      chunk_id: "c1",
      doc_id: "d1",
      text: "The elements of negligence are duty, breach, causation, and damages.",
      doc_title: "Restatement (Second) of Torts",
      section_number: "281",
      score: 0.92,
    },
  ],
  citations: [],
  confidence: {
    faithfulness: 0.95,
    answer_relevance: 0.9,
    context_precision: 0.88,
    context_recall: 0.85,
    overall: 0.9,
  },
  hallucination: {
    score: 0.1,
    verdict: "low",
    findings: [],
  },
  verification: {
    verified_citations: 1,
    unverified_citations: 0,
    missing_citations: 0,
    average_overlap: 0.91,
    verdict: "verified",
  },
  quality_score: 0.95,
  latency_ms: 1250,
  tokens: 180,
  created_at: "2026-01-01T00:00:01Z",
};

describe("MessageItem", () => {
  it("renders user messages with the user label", () => {
    renderMessage(USER_MESSAGE);
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("What is negligence?")).toBeInTheDocument();
  });

  it("renders assistant markdown content", () => {
    renderMessage(ASSISTANT_MESSAGE);
    expect(screen.getByText("Legisight")).toBeInTheDocument();
    expect(screen.getByText(/requires four elements/)).toBeInTheDocument();
  });

  it("shows sources and quality metrics", () => {
    renderMessage(ASSISTANT_MESSAGE);
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText(/Restatement/)).toBeInTheDocument();
    expect(screen.getByText(/92%/)).toBeInTheDocument();
    expect(screen.getByText(/1\.3s/)).toBeInTheDocument();
    expect(screen.getByText(/180 tokens/)).toBeInTheDocument();
    expect(screen.getByText(/quality 95%/)).toBeInTheDocument();
  });

  it("shows verification and hallucination verdicts", () => {
    renderMessage(ASSISTANT_MESSAGE);
    expect(screen.getByText("Citations verified")).toBeInTheDocument();
    expect(screen.getByText("Low hallucination risk")).toBeInTheDocument();
    expect(screen.getByText("Answer quality")).toBeInTheDocument();
  });
});
