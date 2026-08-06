"use client";

import * as React from "react";
import { Activity, ShieldCheck, Gauge } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RequireAuth } from "@/components/require-auth";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import type { Conversation, ConversationDetail, Message } from "@/lib/types";

function extractScores(detail: ConversationDetail): {
  quality: number[];
  confidence: number[];
} {
  const quality: number[] = [];
  const confidence: number[] = [];
  for (const message of detail.messages) {
    if (message.role !== "assistant") continue;
    if (message.quality_score > 0) quality.push(message.quality_score);
    if (message.confidence?.overall != null) confidence.push(message.confidence.overall);
  }
  return { quality, confidence };
}

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

export default function EvalPage() {
  const user = useAuthStore((state) => state.user);
  const [conversations, setConversations] = React.useState<Conversation[]>([]);
  const [details, setDetails] = React.useState<Record<string, ConversationDetail>>({});
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const data = await api.get<{ items: Conversation[]; total: number }>("/api/conversations", {
          limit: 50,
        });
        setConversations(data.items);
        const detailMap: Record<string, ConversationDetail> = {};
        await Promise.all(
          data.items.slice(0, 20).map(async (c) => {
            try {
              detailMap[c.id] = await api.get<ConversationDetail>(`/api/conversations/${c.id}`);
            } catch {
              // skip
            }
          }),
        );
        setDetails(detailMap);
      } finally {
        setLoading(false);
      }
    })();
  }, [user]);

  const allAssistantMessages: { conversation: Conversation; message: Message }[] = [];
  for (const conversation of conversations) {
    const detail = details[conversation.id];
    for (const message of detail?.messages ?? []) {
      if (message.role === "assistant") {
        allAssistantMessages.push({ conversation, message });
      }
    }
  }
  const qualityScores = allAssistantMessages.map((m) => m.message.quality_score).filter((s) => s > 0);
  const overallQuality = average(qualityScores);

  return (
    <RequireAuth>
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="flex items-center gap-2">
          <Activity className="h-6 w-6 text-primary" />
          <h1 className="text-3xl font-bold">Evaluation</h1>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Quality metrics computed on your recent verified answers.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Gauge className="h-4 w-4" />
                Avg quality
              </div>
              <p className="mt-2 text-3xl font-bold">
                {overallQuality > 0 ? `${Math.round(overallQuality * 100)}%` : "—"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <ShieldCheck className="h-4 w-4" />
                Verified answers
              </div>
              <p className="mt-2 text-3xl font-bold">
                {
                  allAssistantMessages.filter(
                    (m) => m.message.verification?.verdict === "verified",
                  ).length
                }
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Activity className="h-4 w-4" />
                Answers scored
              </div>
              <p className="mt-2 text-3xl font-bold">{qualityScores.length}</p>
            </CardContent>
          </Card>
        </div>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-base">Recent answers</CardTitle>
            <CardDescription>
              Assistant messages with quality, citation, and hallucination scores.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">Loading...</p>
            ) : allAssistantMessages.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No scored answers yet. Start a conversation to generate evaluated responses.
              </p>
            ) : (
              <div className="divide-y">
                {allAssistantMessages.slice().reverse().map(({ conversation, message }) => {
                  const quality = Math.round(message.quality_score * 100);
                  const confidence = message.confidence
                    ? Math.round(message.confidence.overall * 100)
                    : null;
                  return (
                    <div key={message.id} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="truncate text-sm font-medium">{conversation.title}</p>
                        <div className="flex shrink-0 items-center gap-2">
                          <Badge variant="outline">quality {quality}%</Badge>
                          {confidence !== null && (
                            <Badge variant="outline">conf {confidence}%</Badge>
                          )}
                          <Badge
                            variant={
                              message.hallucination?.verdict === "high"
                                ? "destructive"
                                : message.hallucination?.verdict === "medium"
                                  ? "warning"
                                  : "success"
                            }
                          >
                            {message.hallucination?.verdict ?? "—"}
                          </Badge>
                        </div>
                      </div>
                      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                        {message.content}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </RequireAuth>
  );
}
