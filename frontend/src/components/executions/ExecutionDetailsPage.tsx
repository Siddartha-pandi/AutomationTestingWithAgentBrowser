"use client";

import React, { useState } from "react";
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  Globe,
  Camera,
  Terminal,
  Code2,
  Sparkles,
  ArrowLeft,
  Download,
  RotateCcw,
  Check,
  Eye,
  X,
  ShieldCheck,
  Layers,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface ExecutionDetailsPageProps {
  executionId?: string;
  projectId: string;
  onNavigate: (view: NavView) => void;
}

export function ExecutionDetailsPage({
  executionId = "exec-run-101",
  projectId,
  onNavigate,
}: ExecutionDetailsPageProps) {
  const [activeTab, setActiveTab] = useState<
    "overview" | "steps" | "screenshots" | "logs" | "dom" | "healing"
  >("overview");

  const [zoomScreenshot, setZoomScreenshot] = useState<string | null>(null);

  const { success, info } = useToast();
  const { confirm } = useConfirm();

  // Execution Details Data
  const execution = {
    id: executionId,
    name: "Customer Onboarding & Email Verification",
    type: "Visual Flow DAG",
    version: "v2.1 (Pinned Immutable)",
    status: "passed",
    environment: "Staging",
    trigger_type: "Manual Operator",
    user: "Lead Administrator",
    start_time: "2026-11-10 09:14:02 IST",
    end_time: "2026-11-10 09:14:06 IST",
    duration: "4.21s",
    session_id: "sess-agent-0412-obscura",
    total_steps: 5,
    passed_steps: 5,
    failed_steps: 0,
  };

  const steps = [
    {
      index: 1,
      name: "Navigate to Staging Portal",
      action: "navigate",
      status: "passed",
      duration: "1.24s",
      start_time: "09:14:02.120",
      input: { url: "https://staging.internal.company.net/auth", timeout: 30 },
      output: { http_status: 200, response_time_ms: 1240 },
      expected: "HTTP 200 OK",
      actual: "HTTP 200 OK",
      error: null,
    },
    {
      index: 2,
      name: "Fill Corporate Email",
      action: "fill",
      status: "passed",
      duration: "0.45s",
      start_time: "09:14:03.360",
      input: { logical_id: "login_email_input", value: "[REDACTED_EMAIL]" },
      output: { value_set: true, characters_typed: 26 },
      expected: "Input populated",
      actual: "Input populated",
      error: null,
    },
    {
      index: 3,
      name: "Click Submit Login",
      action: "click",
      status: "passed",
      duration: "0.62s",
      start_time: "09:14:03.810",
      input: { logical_id: "login_submit_btn", strategy: "deterministic_multi_factor" },
      output: { clicked: true, confidence: 0.984 },
      expected: "Element interactive & clicked",
      actual: "Clicked uniquely",
      error: null,
    },
    {
      index: 4,
      name: "Assert URL Contains Dashboard",
      action: "assert_url",
      status: "passed",
      duration: "0.15s",
      start_time: "09:14:04.430",
      input: { expected_substring: "/dashboard" },
      output: { current_url: "https://staging.internal.company.net/dashboard" },
      expected: "Contains '/dashboard'",
      actual: "https://staging.internal.company.net/dashboard",
      error: null,
    },
    {
      index: 5,
      name: "Capture Post-Login Viewport",
      action: "screenshot",
      status: "passed",
      duration: "0.85s",
      start_time: "09:14:04.580",
      input: { full_page: true, filename: "dashboard_post_login.png" },
      output: { path: "./reports/screenshots/live_01.png", size_bytes: 142850 },
      expected: "Screenshot captured",
      actual: "Saved (142 KB)",
      error: null,
    },
  ];

  const screenshots = [
    {
      id: "sc-1",
      name: "dashboard_post_login.png",
      step: "Step 5: Capture Post-Login Viewport",
      time: "09:14:05 IST",
      url: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='350' viewBox='0 0 600 350'><rect width='600' height='350' fill='%230f172a'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%2338bdf8' font-family='sans-serif' font-size='16'>Step 5: Viewport Capture Post-Login</text></svg>",
    },
  ];

  const logs = [
    { level: "INFO", time: "09:14:02.110", msg: "Agent Browser CLI 0.41.2 daemon spawned." },
    { level: "DEBUG", time: "09:14:02.150", msg: "Domain whitelist checked. Target allowed: staging.internal.company.net" },
    { level: "INFO", time: "09:14:03.360", msg: "Input sanitized and redacted for parameter 'user_email'." },
    { level: "DEBUG", time: "09:14:03.810", msg: "Deterministic multi-factor element search resolved in 14ms." },
    { level: "INFO", time: "09:14:04.580", msg: "Full-page screenshot persisted with SHA-256 integrity hash." },
    { level: "INFO", time: "09:14:05.430", msg: "Flow execution completed with return code 0." },
  ];

  const handleRerun = () => {
    confirm({
      title: "Rerun Execution",
      message: `Rerun flow '${execution.name}' using pinned version '${execution.version}'?`,
      confirmText: "Trigger Rerun",
      variant: "primary",
      onConfirm: () => {
        info("Rerun Dispatched", "Dispatched new background Celery execution task.");
        onNavigate("executions_running");
      },
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate("executions_history")}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-bold text-[#2563EB]">
                {execution.id}
              </span>
              <h1 className="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">
                {execution.name}
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Pinned to <strong>{execution.version}</strong> • Environment: <strong>{execution.environment}</strong> • Duration: {execution.duration}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="capitalize">{execution.status}</span>
          </span>

          <button
            onClick={handleRerun}
            className="px-3.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition"
          >
            <RotateCcw className="w-3.5 h-3.5 text-blue-500" />
            <span>Rerun Safe</span>
          </button>
        </div>
      </div>

      {/* 6 Tabs Navigation Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 flex items-center gap-2 text-xs">
        {[
          { id: "overview", label: "Overview", icon: Activity },
          { id: "steps", label: `Steps (${steps.length})`, icon: Layers },
          { id: "screenshots", label: `Screenshots (${screenshots.length})`, icon: Camera },
          { id: "logs", label: `Logs (${logs.length})`, icon: Terminal },
          { id: "dom", label: "DOM Snapshots", icon: Code2 },
          { id: "healing", label: "Self-Healing Events", icon: Sparkles },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-1.5 px-4 py-2.5 font-bold border-b-2 transition ${
                isActive
                  ? "border-[#2563EB] text-[#2563EB] dark:text-blue-400"
                  : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Triggered By</span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-1">{execution.user}</p>
              <span className="text-[10px] text-slate-500">{execution.trigger_type}</span>
            </div>

            <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Start Time</span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-1">{execution.start_time}</p>
              <span className="text-[10px] text-slate-500">Asia/Kolkata</span>
            </div>

            <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Total Duration</span>
              <p className="text-sm font-bold font-mono text-emerald-600 mt-1">{execution.duration}</p>
              <span className="text-[10px] text-slate-500">5/5 steps passed</span>
            </div>

            <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Browser Engine</span>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-1">agent-browser v0.41.2</p>
              <span className="text-[10px] text-blue-600 font-mono">Isolated Subprocess</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: STEPS */}
      {activeTab === "steps" && (
        <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                  <th className="py-3 px-3">#</th>
                  <th className="py-3 px-3">Step Name</th>
                  <th className="py-3 px-3">Action</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Duration</th>
                  <th className="py-3 px-3">Expected vs Actual</th>
                  <th className="py-3 px-3">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {steps.map((st) => (
                  <tr key={st.index} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                    <td className="py-3 px-3 font-mono font-bold text-slate-400">{st.index}</td>
                    <td className="py-3 px-3 font-semibold text-slate-900 dark:text-slate-100">{st.name}</td>
                    <td className="py-3 px-3">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                        {st.action}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-emerald-600 font-bold flex items-center gap-1 text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Passed</span>
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-500">{st.duration}</td>
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-700 dark:text-slate-300">
                      <div>Exp: {st.expected}</div>
                      <div className="text-emerald-600">Act: {st.actual}</div>
                    </td>
                    <td className="py-3 px-3 text-slate-400">{st.error || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SCREENSHOTS */}
      {activeTab === "screenshots" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {screenshots.map((s) => (
            <div
              key={s.id}
              onClick={() => setZoomScreenshot(s.url)}
              className="p-3 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2 cursor-pointer group hover:border-blue-500 transition"
            >
              <div className="aspect-video bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center">
                <img src={s.url} alt={s.name} className="w-full h-full object-contain group-hover:scale-105 transition" />
              </div>
              <div className="text-xs">
                <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">{s.name}</div>
                <div className="text-[10px] text-slate-400">{s.step} • {s.time}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 4: LOGS */}
      {activeTab === "logs" && (
        <div className="p-4 rounded-2xl bg-slate-950 text-slate-200 font-mono text-xs space-y-2 max-h-96 overflow-y-auto scrollbar-thin">
          {logs.map((l, idx) => (
            <div key={idx} className="flex items-start gap-3 leading-tight">
              <span className="text-slate-500 shrink-0">{l.time}</span>
              <span
                className={`font-bold shrink-0 ${
                  l.level === "INFO"
                    ? "text-blue-400"
                    : l.level === "DEBUG"
                    ? "text-purple-400"
                    : "text-amber-400"
                }`}
              >
                [{l.level}]
              </span>
              <span className="text-slate-300 break-all">{l.msg}</span>
            </div>
          ))}
        </div>
      )}

      {/* TAB 5: DOM SNAPSHOTS */}
      {activeTab === "dom" && (
        <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 dark:text-slate-100">Synchronized Accessibility Snapshot</h3>
            <span className="font-mono text-[10px] text-slate-400">Captured at Step 4</span>
          </div>
          <div className="p-4 rounded-xl bg-slate-950 font-mono text-[11px] text-emerald-400 overflow-x-auto">
            {`<main role="main" id="dashboard-root">\n  <nav class="sidebar" role="navigation">\n  <div class="user-profile" role="region" aria-label="Administrator">\n</main>`}
          </div>
        </div>
      )}

      {/* TAB 6: SELF-HEALING EVENTS */}
      {activeTab === "healing" && (
        <div className="p-6 text-center bg-white dark:bg-[#161F30] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2">
          <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
          <h3 className="font-bold text-sm text-slate-800 dark:text-slate-200">Zero Mutations Required</h3>
          <p className="text-xs text-slate-400">
            All selectors resolved with 100% attribute stability on first attempt. No self-healing triggered.
          </p>
        </div>
      )}

      {/* Lightbox Zoom Modal */}
      {zoomScreenshot && (
        <div
          onClick={() => setZoomScreenshot(null)}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm cursor-zoom-out"
        >
          <img src={zoomScreenshot} alt="Zoom Preview" className="max-w-4xl max-h-[85vh] rounded-xl shadow-2xl" />
        </div>
      )}
    </div>
  );
}
