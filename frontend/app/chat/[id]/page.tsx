"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useChatStore } from "@/stores/chat";
import { Sidebar } from "@/components/chat/sidebar";
import { ChatView } from "@/components/chat/chat-view";
import { RequireAuth } from "@/components/require-auth";

export default function ConversationPage() {
  const params = useParams<{ id: string }>();
  const { loadConversation, clearActive } = useChatStore();

  useEffect(() => {
    clearActive();
    if (params.id) {
      loadConversation(params.id);
    }
  }, [params.id, loadConversation, clearActive]);

  return (
    <RequireAuth>
      <div className="flex h-[calc(100vh-4rem)]">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <ChatView />
        </main>
      </div>
    </RequireAuth>
  );
}
