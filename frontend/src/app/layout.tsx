import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/common/ThemeProvider";
import { ToastProvider } from "@/components/common/ToastProvider";
import { ConfirmProvider } from "@/components/common/ConfirmModal";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "Enterprise Browser Automation & Deterministic Testing Platform",
  description: "Enterprise SaaS platform for visual browser flow automation, deterministic testing, DOM inspection, and rule-based self-healing with Zero-AI company data guarantee.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider>
          <ToastProvider>
            <ConfirmProvider>
              <AuthProvider>
                {children}
              </AuthProvider>
            </ConfirmProvider>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
