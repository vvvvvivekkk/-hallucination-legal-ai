"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Scale, FileX2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageItem } from "@/components/chat/message-item";
import { api } from "@/lib/api";
import type { ShareView } from "@/lib/types";

export default function SharePage() {
  const params = useParams<{ slug: string }>();
  const [share, setShare] = React.useState<ShareView | null>(null);
  const [notFound, setNotFound] = React.useState(false);

  React.useEffect(() => {
    if (!params.slug) return;
    setShare(null);
    setNotFound(false);
    api
      .get<ShareView>(`/api/share/${params.slug}`)
      .then(setShare)
      .catch(() => setNotFound(true));
  }, [params.slug]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      {notFound ? (
        <div className="flex flex-col items-center py-24 text-center">
          <FileX2 className="h-12 w-12 text-muted-foreground" />
          <h1 className="mt-4 text-xl font-semibold">Shared conversation not found</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            This link is invalid or has been revoked.
          </p>
        </div>
      ) : !share ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <>
          <div className="mb-8 border-b pb-6">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Scale className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wide">Shared via Legisight</span>
            </div>
            <h1 className="mt-2 text-2xl font-bold">{share.title}</h1>
          </div>
          {share.messages.length === 0 ? (
            <p className="py-16 text-center text-sm text-muted-foreground">
              This conversation has no messages.
            </p>
          ) : (
            <div className="divide-y rounded-lg border">
              {share.messages.map((message) => (
                <MessageItem key={message.id} message={message} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
