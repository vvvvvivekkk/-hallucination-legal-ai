import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Header } from "@/components/header";

export const metadata: Metadata = {
  title: {
    default: "Legisight — Verified Legal AI Research",
    template: "%s · Legisight",
  },
  description:
    "Legal research assistant that grounds every answer in cited primary sources and verifies claims against them to reduce hallucinations.",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <footer className="border-t py-6">
              <div className="container flex flex-col items-center justify-between gap-2 text-sm text-muted-foreground sm:flex-row">
                <p>© {new Date().getFullYear()} Legisight. Legal AI research platform.</p>
                <p className="text-xs">Not a substitute for licensed legal counsel.</p>
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
