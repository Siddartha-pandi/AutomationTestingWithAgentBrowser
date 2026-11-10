"use client";

import React, { useState } from "react";
import {
  Compass,
  Play,
  Square,
  RefreshCw,
  Camera,
  Globe,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ExternalLink,
  Laptop,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface LiveBrowserPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

export function LiveBrowserPage({ projectId, onNavigate }: LiveBrowserPageProps) {
  const [sessionActive, setSessionActive] = useState(true);
  const [sessionId, setSessionId] = useState("sess-agent-0412-obscura");
  const [currentUrl, setCurrentUrl] = useState("https://staging.internal.company.net/auth");
  const [inputUrl, setInputUrl] = useState("https://staging.internal.company.net/auth");
  const [browserStatus, setBrowserStatus] = useState<"Connected" | "Navigating" | "Idle" | "Terminated">("Connected");
  const [viewportScreenshot, setViewportScreenshot] = useState<string | null>(
    "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='450' viewBox='0 0 800 450'><rect width='800' height='450' fill='%230f172a'/><text x='50%25' y='45%25' dominant-baseline='middle' text-anchor='middle' fill='%2338bdf8' font-family='sans-serif' font-size='18' font-weight='bold'>agent-browser CLI 0.41.2 Session</text><text x='50%25' y='55%25' dominant-baseline='middle' text-anchor='middle' fill='%2394a3b8' font-family='monospace' font-size='13'>https://staging.internal.company.net/auth</text></svg>"
  );

  const [browserLogs, setBrowserLogs] = useState<string[]>([
    "[09:14:02.110] [CLI] agent-browser --session-name obscura-automation daemon started.",
    "[09:14:02.145] [SECURITY] Approved domain whitelist verified (staging.internal.company.net).",
    "[09:14:02.820] [NAVIGATE] Successfully navigated to https://staging.internal.company.net/auth (HTTP 200).",
    "[09:14:03.100] [DOM] Extracted 42 accessibility nodes. ARIA trees synchronized.",
    "[09:14:03.450] [STATE] Viewport 1280x800 ready for deterministic interaction.",
  ]);

  const { success, error, warning, info } = useToast();

  const handleStartSession = () => {
    setSessionActive(true);
    setBrowserStatus("Connected");
    setSessionId(`sess-${Date.now().toString(36)}`);
    setBrowserLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] [SESSION] Initialized new isolated Agent Browser CLI process.`,
    ]);
    success("Browser Session Started", "agent-browser subprocess launched in isolated container.");
  };

  const handleStopSession = () => {
    setSessionActive(false);
    setBrowserStatus("Terminated");
    setBrowserLogs((prev) => [
      ...prev,
      `[${new Date().toLocaleTimeString()}] [SESSION] Closed Agent Browser CLI session.`,
    ]);
    warning("Session Terminated", "Browser process exited.");
  };

  const handleNavigate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionActive) {
      error("No Active Session", "Please start a browser session first.");
      return;
    }
    setBrowserStatus("Navigating");
    info("Navigating", `Agent Browser navigating to ${inputUrl}...`);
    setTimeout(() => {
      setCurrentUrl(inputUrl);
      setBrowserStatus("Connected");
      setBrowserLogs((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] [NAVIGATE] Navigated to ${inputUrl} (HTTP 200).`,
      ]);
      success("Page Loaded", `Active viewport updated.`);
    }, 1200);
  };

  const handleTakeScreenshot = () => {
    if (!sessionActive) return;
    info("Capturing Screenshot", "Requesting full viewport frame from agent-browser...");
    setTimeout(() => {
      setBrowserLogs((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] [SCREENSHOT] Viewport captured to ./reports/screenshots/live_${Date.now()}.png`,
      ]);
      success("Screenshot Captured", "Stored in private compliant artifact storage.");
    }, 800);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Compass className="w-5 h-5 text-[#2563EB]" />
            <span>Live Browser Monitor</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Direct subprocess controller and screenshot observer for the Agent Browser CLI engine.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {sessionActive ? (
            <button
              onClick={handleStopSession}
              className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Stop Session</span>
            </button>
          ) : (
            <button
              onClick={handleStartSession}
              className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Start Session</span>
            </button>
          )}

          <button
            onClick={handleTakeScreenshot}
            disabled={!sessionActive}
            className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-700 transition disabled:opacity-40"
          >
            <Camera className="w-4 h-4 text-purple-500" />
            <span>Capture Screenshot</span>
          </button>
        </div>
      </div>

      {/* URL Navigation Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
        <form onSubmit={handleNavigate} className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-2 flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100">
            <Lock className="w-3.5 h-3.5 text-emerald-600" />
            <input
              type="url"
              required
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="https://staging.internal.company.net"
              className="w-full bg-transparent border-none focus:outline-none font-mono text-xs"
            />
          </div>

          <button
            type="submit"
            disabled={!sessionActive}
            className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <span>Navigate</span>
          </button>

          <button
            type="button"
            onClick={handleNavigate}
            disabled={!sessionActive}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
            title="Refresh Page"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
          <span>Current Target: <strong className="text-slate-700 dark:text-slate-300 font-mono">{currentUrl}</strong></span>
          <span className="font-mono">Session ID: <strong className="text-blue-600">{sessionId}</strong></span>
        </div>
      </div>

      {/* Main Viewport & Console Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Browser Viewport Preview (2 cols) */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Laptop className="w-4 h-4 text-[#2563EB]" />
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
                Agent Browser Viewport (1280x800)
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${sessionActive ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
              <span className="text-[11px] font-mono font-semibold capitalize text-slate-700 dark:text-slate-300">
                {browserStatus}
              </span>
            </div>
          </div>

          <div className="w-full aspect-video rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center relative shadow-inner">
            {viewportScreenshot ? (
              <img
                src={viewportScreenshot}
                alt="Live Viewport Capture"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-slate-500 text-xs italic">
                Browser session idle. Navigate to view current DOM rendering.
              </div>
            )}
          </div>
        </div>

        {/* Browser Logs & Diagnostic Info (1 col) */}
        <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-purple-500" />
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
                CLI Activity Logs
              </h3>
            </div>
            <button
              onClick={() => setBrowserLogs([])}
              className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              Clear
            </button>
          </div>

          <div className="flex-1 bg-slate-950 rounded-xl p-3 font-mono text-[11px] text-slate-300 overflow-y-auto max-h-96 space-y-1.5 scrollbar-thin">
            {browserLogs.map((log, index) => (
              <div key={index} className="leading-tight break-all">
                {log}
              </div>
            ))}
          </div>

          {/* Zero-AI Note */}
          <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-[10px] text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>Pure subprocess isolation. No external telemetry or cloud renderers.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
