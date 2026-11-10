"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Lock, ArrowRight, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { AppContextProvider, useApp } from "@/context/AppContext";
import { AppShell } from "@/components/layout/AppShell";

function AuthenticatedShellWrapper({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { currentView, setCurrentView, currentProject } = useApp();

  return (
    <AppShell
      currentView={currentView}
      onNavigate={setCurrentView}
      user={user}
      onLogout={logout}
      currentProject={currentProject}
    >
      {children}
    </AppShell>
  );
}

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0B0F17] flex flex-col items-center justify-center text-white space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <div className="text-sm font-medium text-slate-300">
          Verifying security token and permissions...
        </div>
        <div className="text-xs text-slate-500 flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>Zero-AI Policy Compliant &bull; Agent Browser Engine</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[#0B0F17] flex items-center justify-center p-6 text-white">
        <div className="max-w-md w-full bg-[#161F30] border border-slate-800 rounded-2xl p-8 shadow-2xl text-center space-y-6">
          <div className="w-14 h-14 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center mx-auto text-blue-400">
            <Lock className="w-7 h-7" />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-bold tracking-tight text-white">
              Authentication Required
            </h2>
            <p className="text-sm text-slate-400">
              You must be signed in with an active enterprise session to access this workspace.
            </p>
          </div>

          <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-400 text-left space-y-1">
            <div className="font-semibold text-slate-300">Security Requirement:</div>
            <div>Valid OAuth2 JWT Bearer Token or corporate session cookie required.</div>
          </div>

          <button
            onClick={() => router.push("/login")}
            className="w-full py-3 bg-[#2563EB] hover:bg-blue-600 text-white font-medium rounded-xl shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2 text-sm"
          >
            <span>Proceed to Enterprise Sign In</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <AppContextProvider>
      <AuthenticatedShellWrapper>{children}</AuthenticatedShellWrapper>
    </AppContextProvider>
  );
}

