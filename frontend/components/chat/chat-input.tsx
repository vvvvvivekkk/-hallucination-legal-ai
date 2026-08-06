"use client";

import { useState } from "react";
import { Square, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useChatStore } from "@/stores/chat";

export function ChatInput() {
  const [value, setValue] = useState("");
  const { sendMessage, stop, streaming } = useChatStore();

  async function handleSubmit() {
    if (!value.trim() || streaming) return;
    const content = value;
    setValue("");
    await sendMessage(content);
  }

  return (
    <div className="border-t bg-background p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Ask a legal question..."
          className="min-h-[56px] max-h-40 resize-none"
          rows={1}
          disabled={streaming}
        />
        {streaming ? (
          <Button
            variant="destructive"
            size="icon"
            onClick={stop}
            aria-label="Stop generating"
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            size="icon"
            onClick={handleSubmit}
            disabled={!value.trim()}
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
      <p className="mt-2 text-center text-xs text-muted-foreground">
        Legisight may make mistakes. Verify important legal claims with cited sources.
      </p>
    </div>
  );
}
