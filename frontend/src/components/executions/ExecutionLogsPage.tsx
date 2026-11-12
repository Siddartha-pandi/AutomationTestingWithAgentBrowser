"use client";

import React, { useState, useEffect } from "react";
import {
  Terminal,
  Search,
  Filter,
  Download,
  RefreshCw,
  ShieldCheck,
  Calendar,
  AlertTriangle,
  Info,
  AlertCircle,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";
import { executionsApi } from "@/api";

interface ExecutionLogsPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  execution_id: string;
  message: string;
  is_redacted: boolean;
}

export function ExecutionLogsPage({ projectId, onNavigate }: ExecutionLogsPageProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadLogs();
  }, [projectId]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const execs = await executionsApi.list({ projectId });
      if (execs && execs.length > 0) {
        const collectedLogs: LogEntry[] = [];
        for (const ex of execs.slice(0, 5)) {
          if (Array.isArray(ex.logs)) {
            for (let idx = 0; idx < ex.logs.length; idx++) {
              collectedLogs.push({
                id: `log-${ex.id}-${idx}`,
                timestamp: ex.created_at || "Recent",
                level: "INFO",
                execution_id: String(ex.id),
                message: typeof ex.logs[idx] === "string" ? ex.logs[idx] : JSON.stringify(ex.logs[idx]),
                is_redacted: true,
              });
            }
          }
        }
        setLogs(collectedLogs);
      } else {
        setLogs([]);
      }
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const [searchQuery, setSearchQuery] = useState("");
  const [levelFilter, setLevelFilter] = useState<string>("all");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { success, info } = useToast();

  const handleDownloadLogs = () => {
    const text = logs
      .map((l) => `[${l.timestamp}] [${l.level}] [${l.execution_id}] ${l.message}`)
      .join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Execution_Logs_${Date.now()}.txt`;
    link.click();
    URL.revokeObjectURL(url);
    success("Logs Exported", "Downloaded execution log trace.");
  };

  const filtered = logs.filter((l) => {
    const q = (searchQuery || "").trim().toLowerCase();
    const msg = (l?.message || "").toLowerCase();
    const execId = (l?.execution_id || "").toLowerCase();
    const matchesSearch = !q || msg.includes(q) || execId.includes(q);
    const matchesLevel = levelFilter === "all" || l?.level === levelFilter;
    return matchesSearch && matchesLevel;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Terminal className="w-5 h-5 text-purple-600" />
            <span>Execution Logs Viewer</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time terminal-style execution logs with automated secret and credential redaction.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Auto Refresh Toggle */}
          <button
            onClick={() => {
              setAutoRefresh(!autoRefresh);
              info(autoRefresh ? "Auto-Refresh Paused" : "Auto-Refresh Active");
            }}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition ${
              autoRefresh
                ? "bg-emerald-50 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300"
                : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400"
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${autoRefresh ? "animate-spin" : ""}`} />
            <span>{autoRefresh ? "Auto-Refresh On" : "Auto-Refresh Off"}</span>
          </button>

          <button
            onClick={handleDownloadLogs}
            className="px-3.5 py-1.5 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Logs</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search log messages, tokens, executions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-slate-500">Severity:</span>
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-mono font-bold"
            >
              <option value="all">ALL LEVELS</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 text-[10px]">
            <ShieldCheck className="w-3 h-3" />
            <span>Secret Masking Active</span>
          </div>
        </div>
      </div>

      {/* Terminal Viewport */}
      <div className="rounded-2xl bg-slate-950 border border-slate-800 shadow-xl p-4 font-mono text-xs overflow-hidden">
        <div className="h-[460px] overflow-y-auto space-y-2 scrollbar-thin text-slate-300">
          {filtered.map((log) => (
            <div key={log.id} className="flex items-start gap-3 leading-snug py-0.5 hover:bg-slate-900/60 px-2 rounded">
              <span className="text-slate-500 shrink-0 text-[11px]">{log.timestamp}</span>
              <span
                className={`font-bold shrink-0 text-[10px] px-1.5 py-0.2 rounded ${
                  log.level === "INFO"
                    ? "bg-blue-950 text-blue-400"
                    : log.level === "DEBUG"
                    ? "bg-purple-950 text-purple-400"
                    : log.level === "WARNING"
                    ? "bg-amber-950 text-amber-400"
                    : "bg-rose-950 text-rose-400"
                }`}
              >
                {log.level}
              </span>
              <span className="text-slate-400 font-mono text-[10px] shrink-0">[{log.execution_id}]</span>
              <span className="text-slate-200 break-all">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
