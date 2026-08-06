"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquare,
  Pin,
  PinOff,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn, timeAgo } from "@/lib/utils";
import { useChatStore } from "@/stores/chat";

export function Sidebar() {
  const router = useRouter();
  const {
    conversations,
    activeConversation,
    pinnedOnly,
    searchQuery,
    sidebarOpen,
    loadConversations,
    createConversation,
    deleteConversation,
    togglePin,
    clearActive,
    setSidebarOpen,
    setPinnedOnly,
    setSearchQuery,
  } = useChatStore();

  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  useEffect(() => {
    loadConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pinnedOnly, searchQuery]);

  const visible = useMemo(() => {
    let items = conversations;
    if (searchQuery) {
      items = items.filter((c) =>
        c.title.toLowerCase().includes(searchQuery.toLowerCase()),
      );
    }
    return items;
  }, [conversations, searchQuery]);

  async function handleNewChat() {
    const id = await createConversation();
    clearActive();
    router.push(`/chat/${id}`);
  }

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r bg-muted/40 transition-transform lg:static lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full",
      )}
    >
      <div className="flex items-center gap-2 p-4">
        <Button className="flex-1 gap-2" onClick={handleNewChat}>
          <Plus className="h-4 w-4" />
          New chat
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        >
          <X className="h-5 w-5" />
        </Button>
      </div>

      <div className="px-4 pb-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="pl-8"
          />
        </div>
      </div>

      <Button
        variant={pinnedOnly ? "secondary" : "ghost"}
        size="sm"
        className="mx-4 mb-2 justify-start gap-2"
        onClick={() => setPinnedOnly(!pinnedOnly)}
      >
        <Pin className="h-3.5 w-3.5" />
        Pinned only
      </Button>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 pb-4">
        {visible.length === 0 ? (
          <p className="px-3 py-8 text-center text-sm text-muted-foreground">
            No conversations yet.
          </p>
        ) : (
          visible.map((conversation) => {
            const active = conversation.id === activeConversation?.id;
            return (
              <div
                key={conversation.id}
                className={cn(
                  "group relative flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-primary/10 text-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground",
                )}
              >
                <button
                  className="flex flex-1 items-center gap-2 overflow-hidden text-left"
                  onClick={() => {
                    router.push(`/chat/${conversation.id}`);
                    setSidebarOpen(false);
                  }}
                >
                  <MessageSquare className="h-4 w-4 shrink-0" />
                  <span className="flex-1 truncate">{conversation.title}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {timeAgo(conversation.updated_at)}
                  </span>
                </button>

                <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => togglePin(conversation.id, !conversation.is_pinned)}
                    aria-label={conversation.is_pinned ? "Unpin" : "Pin"}
                  >
                    {conversation.is_pinned ? (
                      <PinOff className="h-3.5 w-3.5" />
                    ) : (
                      <Pin className="h-3.5 w-3.5" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setConfirmDelete(conversation.id)}
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </nav>

      {confirmDelete && (
        <div className="absolute inset-0 z-50 flex items-end justify-center bg-background/80 p-4 backdrop-blur-sm lg:items-center">
          <div className="w-full max-w-sm rounded-lg border bg-card p-6 shadow-lg">
            <h3 className="text-lg font-semibold">Delete conversation?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              This will permanently delete this conversation and its messages.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={async () => {
                  await deleteConversation(confirmDelete);
                  setConfirmDelete(null);
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
