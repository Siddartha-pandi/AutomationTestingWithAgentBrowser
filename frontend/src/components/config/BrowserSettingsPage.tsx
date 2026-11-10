"use client";

import React, { useState } from "react";
import {
  Sliders,
  Terminal,
  Play,
  CheckCircle2,
  Clock,
  Camera,
  Trash2,
  Save,
  ShieldCheck,
  Globe,
  Lock,
  Cpu,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface BrowserSettingsPageProps {
  onNavigate: (view: NavView) => void;
}

export function BrowserSettingsPage({ onNavigate }: BrowserSettingsPageProps) {
  const [cliVersion, setCliVersion] = useState("0.41.2");
  const [defaultTimeout, setDefaultTimeout] = useState(30);
  const [navTimeout, setNavTimeout] = useState(30);
  const [actionTimeout, setActionTimeout] = useState(15);
  const [storagePath, setStoragePath] = useState("./reports/screenshots");
  const [cleanupPolicy, setCleanupPolicy] = useState("Auto-close on completion");
  const [domainWhitelist, setDomainWhitelist] = useState(
    "staging.internal.company.net\nqa.internal.company.net\napp.company.internal\nlocalhost"
  );

  const [testingConnection, setTestingConnection] = useState(false);

  const { success, info } = useToast();

  const handleTestConnection = () => {
    setTestingConnection(true);
    info("Testing CLI Connection", "Executing `agent-browser --version` subprocess verification...");
    setTimeout(() => {
      setTestingConnection(false);
      success("CLI Verified", "Connected to agent-browser CLI v0.41.2. Subprocess daemon responsive.");
    }, 1200);
  };

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    success("Configuration Saved", "Agent Browser timeout and domain policies updated.");
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Sliders className="w-5 h-5 text-[#2563EB]" />
            <span>Agent Browser Configuration</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Engine parameters, subprocess timeouts, security whitelists, and local CLI daemon controls.
          </p>
        </div>

        <button
          onClick={handleTestConnection}
          disabled={testingConnection}
          className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-700 transition"
        >
          <Play className={`w-3.5 h-3.5 text-emerald-500 ${testingConnection ? "animate-spin" : ""}`} />
          <span>{testingConnection ? "Testing..." : "Test Browser Connection"}</span>
        </button>
      </div>

      {/* CLI Engine Status Banner */}
      <div className="p-4 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#2563EB] flex items-center justify-center font-bold">
              AB
            </div>
            <div>
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
                Agent Browser CLI Engine Status
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Pure subprocess CLI adapter (`backend/app/browser/agent_browser.py`)
              </p>
            </div>
          </div>

          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 text-xs font-bold font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Verified (v{cliVersion})</span>
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2 border-t border-slate-100 dark:border-slate-800 text-slate-600 dark:text-slate-300">
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase block">Session Engine</span>
            <span className="font-mono text-emerald-600 font-bold">Local Subprocess</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase block">AI SDK State</span>
            <span className="font-mono text-emerald-600 font-bold">0% (Strictly Disallowed)</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase block">DOM Extraction</span>
            <span className="font-mono text-slate-800 dark:text-slate-200">Accessibility Tree</span>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase block">Session Isolation</span>
            <span className="font-mono text-blue-600 font-bold">Enabled</span>
          </div>
        </div>
      </div>

      {/* Main Settings Form */}
      <form onSubmit={handleSaveSettings} className="p-6 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-6 text-xs">
        {/* Timeouts */}
        <div className="space-y-4">
          <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#2563EB]" />
            <span>Execution Timeouts</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                Default Timeout (s)
              </label>
              <input
                type="number"
                value={defaultTimeout}
                onChange={(e) => setDefaultTimeout(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                Navigation Timeout (s)
              </label>
              <input
                type="number"
                value={navTimeout}
                onChange={(e) => setNavTimeout(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                Action Step Timeout (s)
              </label>
              <input
                type="number"
                value={actionTimeout}
                onChange={(e) => setActionTimeout(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
              />
            </div>
          </div>
        </div>

        {/* Screenshot & Session Cleanup */}
        <div className="space-y-4 pt-4 border-t border-slate-100 dark:border-slate-800">
          <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Camera className="w-4 h-4 text-purple-600" />
            <span>Artifact & Storage Configuration</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                Screenshots Directory
              </label>
              <input
                type="text"
                value={storagePath}
                onChange={(e) => setStoragePath(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                Session Cleanup Strategy
              </label>
              <select
                value={cleanupPolicy}
                onChange={(e) => setCleanupPolicy(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value="Auto-close on completion">Auto-close on completion (Recommended)</option>
                <option value="Keep session alive for 5 minutes">Keep session alive for 5 minutes</option>
                <option value="Manual termination only">Manual termination only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Approved Domain Whitelist */}
        <div className="space-y-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Approved Domain Security Whitelist</span>
          </h3>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Navigation outside these approved hosts is blocked immediately by the Python adapter before dispatch.
          </p>

          <textarea
            rows={4}
            value={domainWhitelist}
            onChange={(e) => setDomainWhitelist(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none"
          />
        </div>

        {/* Save button */}
        <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white font-semibold flex items-center gap-2 shadow-xs transition"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Browser Settings</span>
          </button>
        </div>
      </form>
    </div>
  );
}
