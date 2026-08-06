"use client";

import { ShieldCheck } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { cn, getConfidenceColor } from "@/lib/utils";
import type { ConfidenceReport } from "@/lib/types";

interface ConfidenceMeterProps {
  confidence: ConfidenceReport;
  compact?: boolean;
}

const METRICS: { key: keyof ConfidenceReport; label: string }[] = [
  { key: "faithfulness", label: "Faithfulness" },
  { key: "answer_relevance", label: "Answer relevance" },
  { key: "context_precision", label: "Context precision" },
  { key: "context_recall", label: "Context recall" },
];

export function ConfidenceMeter({ confidence, compact = false }: ConfidenceMeterProps) {
  if (!confidence || typeof confidence.overall !== "number") return null;

  const overall = Math.round(confidence.overall * 100);

  return (
    <div className="mt-3 space-y-2 rounded-md border bg-muted/30 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Answer quality
        </div>
        <span className={cn("text-sm font-semibold", getConfidenceColor(overall / 100))}>
          {overall}%
        </span>
      </div>
      <Progress value={overall} className="h-2" />
      {!compact && (
        <div className="grid grid-cols-2 gap-2 pt-1">
          {METRICS.map((metric) => {
            const value = Math.round(((confidence[metric.key] as number) ?? 0) * 100);
            return (
              <div key={metric.key} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{metric.label}</span>
                <span className="font-medium">{value}%</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
