"use client";

import { User, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/types";
import { Markdown } from "@/components/chat/markdown";
import { CitationPanel, StreamingIndicator } from "@/components/chat/citation-panel";
import { ConfidenceMeter } from "@/components/chat/confidence-meter";
import { HallucinationAlert } from "@/components/chat/hallucination-alert";
import { VerificationPanel } from "@/components/chat/verification-panel";

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "group flex gap-3 px-4 py-5 sm:px-6",
        isUser ? "bg-muted/30" : "bg-background",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-white",
          isUser ? "bg-primary" : "bg-slate-700",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <span>{isUser ? "You" : "Legisight"}</span>
          {message.streaming && <StreamingIndicator />}
        </div>

        {message.content && <Markdown content={message.content} />}

        {!isUser && (
          <>
            <CitationPanel sources={message.sources} />
            {message.verification && <VerificationPanel report={message.verification} />}
            {message.hallucination && <HallucinationAlert report={message.hallucination} />}
            {message.confidence && <ConfidenceMeter confidence={message.confidence} />}

            {(message.latency_ms > 0 || message.tokens > 0) && (
              <p className="text-xs text-muted-foreground">
                {message.latency_ms > 0 && `${(message.latency_ms / 1000).toFixed(1)}s`}
                {message.latency_ms > 0 && message.tokens > 0 && " · "}
                {message.tokens > 0 && `${message.tokens} tokens`}
                {message.quality_score > 0 && ` · quality ${(message.quality_score * 100).toFixed(0)}%`}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
