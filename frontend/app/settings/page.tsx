"use client";

import * as React from "react";
import { KeyRound, LogOut, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { RequireAuth } from "@/components/require-auth";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { updateProfile, changePassword, saving, error, success } = useSettingsStore();

  const [fullName, setFullName] = React.useState(user?.full_name ?? "");
  const [email, setEmail] = React.useState(user?.email ?? "");
  const [currentPassword, setCurrentPassword] = React.useState("");
  const [newPassword, setNewPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [passwordError, setPasswordError] = React.useState("");

  React.useEffect(() => {
    setFullName(user?.full_name ?? "");
    setEmail(user?.email ?? "");
  }, [user]);

  async function handleProfile(e: React.FormEvent) {
    e.preventDefault();
    await updateProfile({ full_name: fullName });
  }

  async function handlePassword(e: React.FormEvent) {
    e.preventDefault();
    setPasswordError("");
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match.");
      return;
    }
    await changePassword(currentPassword, newPassword);
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  }

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <RequireAuth>
      <div className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="mt-2 text-sm text-muted-foreground">Manage your profile, security, and session.</p>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="h-4 w-4" />
              Profile
            </CardTitle>
            <CardDescription>Your account details shown on shared conversations.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleProfile} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="fullName">Full name</Label>
                <Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={email} disabled />
                <p className="text-xs text-muted-foreground">
                  Email changes are not currently supported. Contact an administrator.
                </p>
              </div>
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save profile"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <KeyRound className="h-4 w-4" />
              Change password
            </CardTitle>
            <CardDescription>Rotate your password to invalidate old sessions.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePassword} className="space-y-4">
              {passwordError && (
                <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {passwordError}
                </p>
              )}
              <div className="space-y-2">
                <Label htmlFor="current">Current password</Label>
                <Input
                  id="current"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new">New password</Label>
                <Input
                  id="new"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm">Confirm new password</Label>
                <Input
                  id="confirm"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
              <Button type="submit" disabled={saving || !currentPassword || !newPassword}>
                {saving ? "Updating..." : "Update password"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {error && (
          <p role="alert" className="mt-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}
        {success && (
          <p className="mt-4 rounded-md bg-success/10 px-3 py-2 text-sm text-success">{success}</p>
        )}

        <Separator className="my-8" />

        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <LogOut className="h-4 w-4" />
              Session
            </CardTitle>
            <CardDescription>Sign out of this device or all devices.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button variant="outline" onClick={handleLogout}>
              Log out
            </Button>
          </CardContent>
        </Card>
      </div>
    </RequireAuth>
  );
}
