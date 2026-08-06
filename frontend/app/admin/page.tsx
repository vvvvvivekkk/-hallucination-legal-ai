"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Shield, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { RequireAuth } from "@/components/require-auth";
import { api } from "@/lib/api";
import { useAuthStore, isAdmin } from "@/stores/auth";
import type { SystemStats, User } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export default function AdminPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const [users, setUsers] = React.useState<User[]>([]);
  const [stats, setStats] = React.useState<SystemStats | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (user && !isAdmin(user)) {
      router.replace("/chat");
      return;
    }
    api
      .get<User[]>("/api/admin/users")
      .then(setUsers)
      .catch((err) => setError("Failed to load users."));
    api
      .get<SystemStats>("/api/admin/stats")
      .then(setStats)
      .catch(() => {});
  }, [user, router]);

  async function updateUser(id: string, patch: { role?: string; is_active?: boolean }) {
    try {
      const updated = await api.patch<User>(`/api/admin/users/${id}`, patch);
      setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
    } catch {
      setError("Update failed.");
    }
  }

  if (user && !isAdmin(user)) return null;

  return (
    <RequireAuth>
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <h1 className="text-3xl font-bold">Admin</h1>
        </div>

        {error && (
          <p role="alert" className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        {stats && (
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Users", value: stats.users },
              { label: "Conversations", value: stats.conversations },
              { label: "Messages", value: stats.messages },
              { label: "Index points", value: stats.qdrant_points },
            ].map((item) => (
              <Card key={item.label}>
                <CardContent className="p-4">
                  <p className="text-2xl font-bold">{item.value}</p>
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4" />
              Users
            </CardTitle>
            <CardDescription>Manage roles and account status.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {users.map((item) => (
                <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="font-medium">{item.full_name || "Unnamed user"}</p>
                    <p className="truncate text-sm text-muted-foreground">{item.email}</p>
                    <p className="text-xs text-muted-foreground">
                      Joined {formatDate(item.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge variant={item.role === "admin" ? "default" : "secondary"}>{item.role}</Badge>
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      Admin
                      <Switch
                        checked={item.role === "admin"}
                        onCheckedChange={(checked) =>
                          updateUser(item.id, { role: checked ? "admin" : "user" })
                        }
                        disabled={item.id === user?.id}
                      />
                    </label>
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      Active
                      <Switch
                        checked={item.is_active}
                        onCheckedChange={(checked) => updateUser(item.id, { is_active: checked })}
                        disabled={item.id === user?.id}
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>
            {users.length === 0 && (
              <p className="py-6 text-center text-sm text-muted-foreground">No users found.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </RequireAuth>
  );
}
