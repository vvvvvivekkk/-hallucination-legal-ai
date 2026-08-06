"use client";

import * as React from "react";
import { FileSearch, Search, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { truncate } from "@/lib/utils";

interface SearchResponse {
  query: string;
  collection: string;
  total: number;
  elapsed_ms: number;
  results: SearchHit[];
}

export default function SearchPage() {
  const [query, setQuery] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<SearchResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.post<SearchResponse>("/api/search", { query, top_k: 20 });
      setResult(response);
    } catch (err) {
      setError("Search failed. Is the backend running and the collection populated?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold">Source search</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Semantic + lexical search over the ingested legal corpus.
        </p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search statutes, cases, regulations..."
            className="pl-9"
          />
        </div>
        <Button type="submit" disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
        </Button>
      </form>

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-8">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {result.total} results for <strong className="text-foreground">“{result.query}”</strong>
            </span>
            <span>{result.elapsed_ms} ms</span>
          </div>
          <div className="mt-4 space-y-3">
            {result.results.map((hit, index) => (
              <Card key={hit.chunk_id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <FileSearch className="h-4 w-4 shrink-0 text-primary" />
                        <span className="truncate text-sm font-semibold">
                          {hit.metadata?.title as string | undefined ?? "Untitled"}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{truncate(hit.text, 320)}</p>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        {typeof hit.metadata?.doc_type === "string" && (
                          <Badge variant="secondary">{hit.metadata.doc_type}</Badge>
                        )}
                        {typeof hit.metadata?.jurisdiction === "string" && (
                          <Badge variant="outline">{hit.metadata.jurisdiction}</Badge>
                        )}
                        {typeof hit.metadata?.year === "number" && (
                          <Badge variant="outline">{hit.metadata.year}</Badge>
                        )}
                      </div>
                    </div>
                    <Badge variant="default">{(hit.score * 100).toFixed(0)}%</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {result && result.results.length === 0 && (
        <div className="py-16 text-center text-sm text-muted-foreground">
          No matches found. Try different keywords.
        </div>
      )}
    </div>
  );
}
