"use client";

import * as React from "react";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useAuthStore } from "@/stores/auth";

export function Providers({ children }: { children: React.ReactNode }) {
  const load = useAuthStore((state) => state.load);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <ThemeProvider>
      <TooltipProvider delayDuration={100}>{children}</TooltipProvider>
    </ThemeProvider>
  );
}
