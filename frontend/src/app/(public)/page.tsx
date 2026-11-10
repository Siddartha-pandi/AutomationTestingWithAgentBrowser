"use client";

import React from "react";
import Link from "next/link";
import {
  Shield,
  Terminal,
  Cpu,
  ArrowRight,
  CheckCircle,
  GitBranch,
  Layers,
  Activity,
  Lock,
  Globe,
  Sliders,
  Sparkles,
} from "lucide-react";

export default function PublicLandingPage() {
  return (
    <div className="flex-1 flex flex-col">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-24 md:pt-28 md:pb-32 bg-gradient-to-b from-[#0B0F17] via-[#0E1524] to-[#0B0F17] border-b border-slate-800/80">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span>Agent Browser CLI v0.41.2 Native Integration</span>
          </div>

          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight">
            Deterministic Browser Flow & Testing Automation for the Enterprise
          </h1>

          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto font-normal">
            A secure multi-user platform for visual workflow orchestration, comprehensive regression testing, and mathematical self-healing without sending confidential company data to third-party AI services.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-8 py-3.5 bg-[#2563EB] hover:bg-blue-600 text-white font-medium rounded-xl shadow-lg shadow-blue-600/30 transition flex items-center justify-center gap-2"
            >
              <span>Launch Platform</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              href="/login"
              className="w-full sm:w-auto px-8 py-3.5 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 font-medium rounded-xl transition flex items-center justify-center gap-2"
            >
              <span>Enterprise Sign In</span>
            </Link>
          </div>

          {/* Compliance Banner */}
          <div className="pt-8 max-w-3xl mx-auto">
            <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 flex items-center justify-center gap-4 text-emerald-400 text-xs sm:text-sm font-medium">
              <Shield className="w-5 h-5 shrink-0 text-emerald-400" />
              <span>
                <strong>Company AI Policy Mandate:</strong> Strict Zero-AI architecture. No LLM APIs, no third-party telemetry, 100% deterministic rule-based algorithms.
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Pillars Section */}
      <section className="py-20 bg-[#0B0F17]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center space-y-3">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Enterprise-Grade Automation Architecture
            </h2>
            <p className="text-sm text-slate-400 max-w-xl mx-auto">
              Engineered with deterministic safety gates, AES-256 encryption, and tamper-resistant audit trails.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-[#161F30] border border-slate-800 rounded-2xl p-6 space-y-4">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <GitBranch className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-semibold text-white">Visual Flow Builder</h3>
              <p className="text-sm text-slate-400">
                Drag-and-drop React Flow canvas supporting 15 deterministic action nodes, conditional branching, loops, and live DAG validation.
              </p>
            </div>

            <div className="bg-[#161F30] border border-slate-800 rounded-2xl p-6 space-y-4">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-semibold text-white">Mathematical Self-Healing</h3>
              <p className="text-sm text-slate-400">
                Normalized Levenshtein distances, Jaccard ancestor sets, and ARIA tree semantics with automated tiers and human-in-the-loop approval.
              </p>
            </div>

            <div className="bg-[#161F30] border border-slate-800 rounded-2xl p-6 space-y-4">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-semibold text-white">Vault & Security Governance</h3>
              <p className="text-sm text-slate-400">
                Write-only AES-256-GCM credential encryption, domain whitelisting, RBAC capability matrices, and append-only audit ledgers.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

