"use client";

import { AlertTriangle, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn, getVerdictColor } from "@/lib/utils";
import type { HallucinationReport } from "@/lib/types";

interface HallucinationAlertProps {
  report: HallucinationReport;
}

function verdictLabel(verdict: string): string {
  switch (verdict) {
    case "low":
      return "Low hallucination risk";
    case "medium":
      return "Medium hallucination risk";
    case "high":
      return "High hallucination risk";
    default:
      return "Hallucination check";
  }
}

export function HallucinationAlert({ report }: HallucinationAlertProps) {
  if (!report) return null;
  const score = Math.round((report.score ?? 0) * 100);

  return (
    <div className="mt-3 rounded-md border bg-muted/30 p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <ShieldAlert className="h-4 w-4 text-amber-500" />
          Hallucination check
        </div>
        <Badge variant={report.verdict === "high" ? "destructive" : report.verdict === "medium" ? "warning" : "success"}>
          {verdictLabel(report.verdict)}
        </Badge>
      </div>
      {report.findings && report.findings.length > 0 && (
        <ul className="mt-2 space-y-1.5 text-xs">
          {report.findings.slice(0, 5).map((finding, index) => (
            <li key={index} className="flex items-start gap-2">
              <AlertTriangle className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", getVerdictColor(finding.severity))} />
              <span className="text-muted-foreground">{finding.detail}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-muted-foreground">
        Score: {score}/100
      </p>
    </div>
  );
}
