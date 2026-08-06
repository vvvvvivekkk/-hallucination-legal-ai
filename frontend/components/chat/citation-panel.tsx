"use client";

import { CheckCircle2, XCircle, FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { SourceChunk } from "@/lib/types";

interface CitationPanelProps {
  sources: SourceChunk[];
}

function scoreLabel(score: number): string {
  if (score >= 0.8) return "High confidence";
  if (score >= 0.6) return "Medium confidence";
  return "Low confidence";
}

function scoreClass(score: number): string {
  if (score >= 0.8) return "bg-emerald-600";
  if (score >= 0.6) return "bg-amber-500";
  return "bg-red-500";
}

export function CitationPanel({ sources }: CitationPanelProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-4">
      <div className="flex items-center gap-2">
        <FileText className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium">Sources</span>
        <span className="text-xs text-muted-foreground">({sources.length})</span>
      </div>
      <div className="mt-2 space-y-2">
        {sources.map((source, index) => {
          const title = `${source.doc_title ?? "Untitled"}${source.section_number ? ` · §${source.section_number}` : ""}${source.page ? ` · p.${source.page}` : ""}`;
          return (
            <Tooltip key={source.chunk_id ?? index}>
              <TooltipTrigger asChild>
                <button className="flex w-full items-start gap-2 rounded-md border bg-muted/40 px-3 py-2 text-left text-xs transition-colors hover:bg-accent">
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold text-white ${scoreClass(source.score)}`}
                  >
                    {index + 1}
                  </span>
                  <span className="flex-1">
                    <span className="block truncate font-medium text-foreground">
                      {title}
                    </span>
                    <span className="block text-muted-foreground">
                      {scoreLabel(source.score)} · {(source.score * 100).toFixed(0)}%
                    </span>
                  </span>
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-md">
                <p className="line-clamp-4">{source.text}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}

export function VerifiedBadge({ verified }: { verified: boolean }) {
  if (verified) {
    return (
      <Badge variant="success" className="gap-1">
        <CheckCircle2 className="h-3 w-3" />
        Verified
      </Badge>
    );
  }
  return (
    <Badge variant="destructive" className="gap-1">
      <XCircle className="h-3 w-3" />
      Unverified
    </Badge>
  );
}

export function StreamingIndicator() {
  return (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot" />
      <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot [animation-delay:200ms]" />
      <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-dot [animation-delay:400ms]" />
    </span>
  );
}
