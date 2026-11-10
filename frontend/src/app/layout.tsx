import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/common/ThemeProvider";
import { ToastProvider } from "@/components/common/ToastProvider";
import { ConfirmProvider } from "@/components/common/ConfirmModal";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "AutomationTestingWithAgentBrowser | Enterprise Flow & Test Automation",
  description: "Enterprise multi-user platform for browser flow automation, deterministic testing, DOM inspection and rule-based self-healing.",
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
