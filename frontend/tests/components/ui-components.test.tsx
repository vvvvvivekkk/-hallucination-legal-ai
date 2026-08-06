import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";
import { ConfidenceMeter } from "@/components/chat/confidence-meter";
import type { ConfidenceReport } from "@/lib/types";

describe("Button", () => {
  it("renders children and default variant class", () => {
    const { container } = render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-primary");
  });

  it("supports ghost variant", () => {
    const { container } = render(<Button variant="ghost">Ghost</Button>);
    expect(container.firstChild).toHaveClass("hover:bg-accent");
  });
});

describe("ConfidenceMeter", () => {
  const confidence: ConfidenceReport = {
    faithfulness: 0.9,
    answer_relevance: 0.8,
    context_precision: 0.7,
    context_recall: 0.6,
    overall: 0.75,
  };

  it("renders overall score and metric labels", () => {
    render(<ConfidenceMeter confidence={confidence} />);
    expect(screen.getByText("Answer quality")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("Faithfulness")).toBeInTheDocument();
    expect(screen.getByText("Context recall")).toBeInTheDocument();
  });

  it("renders nothing when confidence is missing", () => {
    const { container } = render(
      <ConfidenceMeter confidence={null as unknown as ConfidenceReport} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
