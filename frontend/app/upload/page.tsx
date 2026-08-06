"use client";

import * as React from "react";
import { FolderOpen, Loader2, RefreshCw, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { RequireAuth } from "@/components/require-auth";
import type { Job } from "@/lib/types";

interface QueueResponse {
  job_id: string;
  status: string;
  message: string;
}

const STATUS_VARIANT: Record<string, "destructive" | "warning" | "success" | "default"> = {
  failed: "destructive",
  running: "warning",
  completed: "success",
};

export default function UploadPage() {
  const [path, setPath] = React.useState("");
  const [enableDedup, setEnableDedup] = React.useState(true);
  const [queued, setQueued] = React.useState<QueueResponse | null>(null);
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadJobs = React.useCallback(async () => {
    try {
      setJobs(await api.get<Job[]>("/api/jobs"));
    } catch {
      // backend may be down
    }
  }, []);

  React.useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 3000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  async function handleIngest() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post<QueueResponse>("/api/ingest", {
        path: path.trim() || undefined,
        enable_dedup: enableDedup,
      });
      setQueued(response);
      await loadJobs();
    } catch {
      setError("Could not queue ingestion. Check the path and backend health.");
    } finally {
      setLoading(false);
    }
  }

  async function handleIndex() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post<QueueResponse>("/api/index", {});
      setQueued(response);
      await loadJobs();
    } catch {
      setError("Could not queue index build.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <RequireAuth>
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-3xl font-bold">Document ingestion</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Queue an ingestion job over a directory of raw legal documents. Files are parsed,
          chunked, and embedded into the vector index.
        </p>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FolderOpen className="h-4 w-4" />
              Ingest a directory
            </CardTitle>
            <CardDescription>
              Leave the path empty to use the server default ingestion directory.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="path">Source path (server-side)</Label>
                <Input
                  id="path"
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  placeholder="e.g. /app/data/raw_documents"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="dedup"
                  type="checkbox"
                  checked={enableDedup}
                  onChange={(e) => setEnableDedup(e.target.checked)}
                  className="h-4 w-4 rounded border-input accent-primary"
                />
                <Label htmlFor="dedup" className="font-normal text-muted-foreground">
                  Enable deduplication
                </Label>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleIngest} disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                  Queue ingestion
                </Button>
                <Button variant="outline" onClick={handleIndex} disabled={loading}>
                  <RefreshCw className="h-4 w-4" />
                  Rebuild index
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {queued && (
          <Card className="mt-6 border-primary/30 bg-primary/5">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Queued</CardTitle>
              <CardDescription>{queued.message}</CardDescription>
            </CardHeader>
            <CardContent className="flex items-center gap-3 text-sm">
              <span className="font-mono text-xs text-muted-foreground">{queued.job_id}</span>
              <Badge>{queued.status}</Badge>
            </CardContent>
          </Card>
        )}

        {error && (
          <p role="alert" className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        <Card className="mt-10">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <RotateCw className="h-4 w-4" />
              Recent jobs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {jobs.map((item) => (
                <li key={item.job_id} className="rounded-md border p-3 text-sm">
                  <div className="flex items-center justify-between gap-4">
                    <span className="flex items-center gap-2 font-medium">
                      {item.kind}
                      <Badge variant={STATUS_VARIANT[item.status] ?? "default"}>{item.status}</Badge>
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {new Date(item.updated_at).toLocaleString()}
                    </span>
                  </div>
                  {item.status === "running" && <Progress value={item.progress} className="mt-2 h-1.5" />}
                  {item.message && <p className="mt-1 text-xs text-muted-foreground">{item.message}</p>}
                  {item.error && <p className="mt-1 text-xs text-destructive">{item.error}</p>}
                </li>
              ))}
            </ul>
            {jobs.length === 0 && (
              <p className="py-4 text-center text-sm text-muted-foreground">No jobs yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </RequireAuth>
  );
}
