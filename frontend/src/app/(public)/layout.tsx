"use client";

import React from "react";
import Link from "next/link";
import { Shield, Terminal, ArrowRight, Sun, Moon, CheckCircle } from "lucide-react";
import { useTheme } from "@/components/common/ThemeProvider";
import { BrowserAutomationLogo } from "@/components/common/BrowserLogo";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen flex flex-col bg-[#0B0F17] text-white">
      {/* Public Navigation Header */}
      <header className="border-b border-slate-800/80 bg-[#0B0F17]/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-3">
              <BrowserAutomationLogo size={36} />
              <div className="flex flex-col">
                <span className="font-semibold text-base tracking-tight text-white leading-tight">
                  AutomationTesting<span className="text-blue-500">WithAgentBrowser</span>
                </span>
                <span className="text-[11px] text-slate-400">Enterprise Flow & Testing Automation</span>
              </div>
            </Link>

            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Zero-AI Policy Compliant</span>
            </div>
          </div>

          <nav className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              title="Toggle theme"
            >
              {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition"
            >
              Sign In
            </Link>

            <Link
              href="/register"
              className="px-4 py-2 text-sm font-medium text-white bg-[#2563EB] hover:bg-blue-600 rounded-lg shadow-md shadow-blue-600/20 transition flex items-center gap-1.5"
            >
              <span>Get Started</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Public Content */}
      <main className="flex-1 flex flex-col">{children}</main>

      {/* Public Footer */}
      <footer className="border-t border-slate-800/80 bg-[#080B11] text-slate-400 text-xs py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <BrowserAutomationLogo size={24} />
            <span>&copy; {new Date().getFullYear()} AutomationTestingWithAgentBrowser. All rights reserved.</span>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>100% Deterministic Rule Engine</span>
            </div>
            <div className="flex items-center gap-1.5 text-blue-400 font-medium">
              <Terminal className="w-3.5 h-3.5" />
              <span>Agent Browser CLI v0.41.2</span>
            </div>
            <span className="text-slate-500">Confidential Corporate Deployment</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

