"use client";

import { BadgeCheck } from "lucide-react";
import { cn, getVerdictColor } from "@/lib/utils";
import type { VerificationReport } from "@/lib/types";

interface VerificationPanelProps {
  report: VerificationReport;
}

function verdictLabel(verdict: string): string {
  switch (verdict) {
    case "verified":
      return "Citations verified";
    case "partially_verified":
      return "Partially verified";
    case "unverified":
      return "Citations not verified";
    default:
      return "Verification";
  }
}

export function VerificationPanel({ report }: VerificationPanelProps) {
  if (!report) return null;
  const total = (report.verified_citations ?? 0) + (report.unverified_citations ?? 0);
  const ratio = total > 0 ? Math.round((report.verified_citations / total) * 100) : 0;

  return (
    <div className="mt-3 rounded-md border bg-muted/30 p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <BadgeCheck className="h-4 w-4 text-primary" />
        <span
          className={cn(
            "font-medium",
            getVerdictColor(
              report.verdict === "verified" ? "low" : report.verdict === "partially_verified" ? "medium" : "high",
            ),
          )}
        >
          {verdictLabel(report.verdict)}
        </span>
      </div>
      <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
        <span>
          Verified: <strong className="text-foreground">{report.verified_citations}</strong>
        </span>
        <span>
          Unverified: <strong className="text-foreground">{report.unverified_citations}</strong>
        </span>
        <span>
          Match: <strong className="text-foreground">{ratio}%</strong>
        </span>
      </div>
    </div>
  );
}
