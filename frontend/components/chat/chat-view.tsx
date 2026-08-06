"use client";

import { useEffect, useRef } from "react";
import { Menu, Scale, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageItem } from "@/components/chat/message-item";
import { ChatInput } from "@/components/chat/chat-input";
import { useChatStore } from "@/stores/chat";

const SUGGESTIONS = [
  "What is the statute of limitations for breach of contract?",
  "Summarize the key holdings of a recent precedent I should know.",
  "Draft a checklist for a residential lease agreement.",
  "What elements are required to establish negligence?",
];

export function ChatView() {
  const { messages, loading, error, streaming, setSidebarOpen } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="flex items-center gap-2 border-b px-4 py-3 lg:hidden">
        <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar">
          <Menu className="h-5 w-5" />
        </Button>
        <span className="text-sm font-medium">Chat</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {error && (
          <div className="mx-auto max-w-3xl px-6 pt-4">
            <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          </div>
        )}

        {loading ? (
          <div className="mx-auto max-w-3xl space-y-4 p-6">
            <Skeleton className="h-10 w-2/3" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : messages.length === 0 ? (
          <div className="mx-auto flex max-w-2xl flex-col items-center px-6 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Scale className="h-8 w-8" />
            </div>
            <h2 className="mt-4 text-2xl font-semibold">Ask a legal question</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Every answer is grounded in cited sources and scored for hallucination risk.
            </p>
            <div className="mt-8 grid w-full gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => useChatStore.getState().sendMessage(suggestion)}
                  className="rounded-lg border bg-card p-4 text-left text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  {suggestion}
                </button>
              ))}
            </div>
            <p className="mt-8 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5" />
              Verified citations · hallucination scoring · export & share
            </p>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl">
            {messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <ChatInput />
    </div>
  );
}
