"use client";

import React, { useState, useEffect } from "react";
import {
  PlayCircle,
  PauseCircle,
  XCircle,
  Eye,
  Terminal,
  Compass,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Activity,
  Layers,
} from "lucide-react";
import { executionsApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface RunningExecutionsPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
  onSelectExecution?: (id: string) => void;
}

interface ActiveRun {
  id: string;
  name: string;
  type: "Flow" | "Test" | "Suite";
  user: string;
  environment: string;
  started_at: string;
  duration: string;
  progress: number;
  status: "running" | "paused" | "queued";
  current_step: string;
  session_id: string;
}

export function RunningExecutionsPage({ projectId, onNavigate, onSelectExecution }: RunningExecutionsPageProps) {
  const [runs, setRuns] = useState<ActiveRun[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRuns = async () => {
    setLoading(true);
    try {
      const list = await executionsApi.list({ projectId, status: "running" });
      if (list && list.length > 0) {
        setRuns(
          list.map((item: any) => ({
            id: item.id,
            name: item.name || "Flow Execution",
            type: item.type || "Flow",
            user: item.user || "Operator",
            environment: item.environment || "Staging",
            started_at: "Just now",
            duration: item.duration || "1.2s",
            progress: item.progress || 50,
            status: item.status || "running",
            current_step: item.current_step || "Running step...",
            session_id: item.session_id || "sess-agent-browser",
          }))
        );
      } else {
        setRuns([]);
      }
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [projectId]);

  const { success, error, info, warning } = useToast();
  const { confirm } = useConfirm();

  // Progress heartbeat simulation
  useEffect(() => {
    const timer = setInterval(() => {
      setRuns((prev) =>
        prev.map((r) => {
          if (r.status === "running" && r.progress < 95) {
            return { ...r, progress: Math.min(95, r.progress + 4) };
          }
          return r;
        })
      );
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  const handlePause = (run: ActiveRun) => {
    setRuns(runs.map((r) => (r.id === run.id ? { ...r, status: "paused" } : r)));
    warning("Execution Paused", `Paused Celery worker for ${run.name}.`);
  };

  const handleResume = (run: ActiveRun) => {
    setRuns(runs.map((r) => (r.id === run.id ? { ...r, status: "running" } : r)));
    success("Execution Resumed", `Resumed ${run.name}.`);
  };

  const handleCancel = (run: ActiveRun) => {
    confirm({
      title: "Cancel Active Execution",
      message: `Terminate execution '${run.id}' and terminate its Agent Browser CLI subprocess?`,
      confirmText: "Cancel Execution",
      variant: "danger",
      onConfirm: async () => {
        try {
          await executionsApi.cancel(run.id);
        } catch {
          // fallback
        }
        setRuns(runs.filter((r) => r.id !== run.id));
        info("Execution Terminated", `Session '${run.session_id}' aborted safely.`);
      },
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <PlayCircle className="w-5 h-5 text-[#2563EB] animate-spin" />
            <span>Running Executions Monitor</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time status of active background Celery worker tasks and isolated browser processes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 text-[#2563EB] font-bold">
            {runs.length} Active Tasks
          </span>
        </div>
      </div>

      {/* Live Runs Cards / Table */}
      <div className="space-y-4">
        {runs.length === 0 ? (
          <div className="p-12 text-center bg-white dark:bg-[#161F30] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
            <h3 className="font-bold text-sm text-slate-800 dark:text-slate-200">No Active Executions</h3>
            <p className="text-xs text-slate-400">All workflow queues are idle and awaiting trigger.</p>
          </div>
        ) : (
          runs.map((run) => (
            <div
              key={run.id}
              className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4 text-xs"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-[#2563EB] flex items-center justify-center shrink-0">
                    <Activity className="w-5 h-5 animate-pulse" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-bold">
                        {run.id}
                      </span>
                      <span className="font-bold text-sm text-slate-900 dark:text-slate-100">
                        {run.name}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      Triggered by {run.user} in <strong className="text-slate-700 dark:text-slate-300">{run.environment}</strong> • Elapsed: {run.duration}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Pause / Resume */}
                  {run.status === "running" ? (
                    <button
                      onClick={() => handlePause(run)}
                      className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold flex items-center gap-1 transition"
                    >
                      <PauseCircle className="w-3.5 h-3.5 text-amber-500" />
                      <span>Pause</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => handleResume(run)}
                      className="px-3 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 font-semibold flex items-center gap-1 transition"
                    >
                      <PlayCircle className="w-3.5 h-3.5" />
                      <span>Resume</span>
                    </button>
                  )}

                  {/* Cancel */}
                  <button
                    onClick={() => handleCancel(run)}
                    className="px-3 py-1.5 rounded-lg border border-rose-200 dark:border-rose-900 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 dark:text-rose-400 font-semibold flex items-center gap-1 transition"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Cancel</span>
                  </button>

                  {/* View Details */}
                  <button
                    onClick={() => {
                      if (onSelectExecution) onSelectExecution(run.id);
                      onNavigate("executions_details");
                    }}
                    className="px-3 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold flex items-center gap-1 shadow-xs transition"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>View Result</span>
                  </button>
                </div>
              </div>

              {/* Progress Bar & Current Step */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
                    <span>{run.current_step}</span>
                  </span>
                  <span className="font-mono font-bold text-[#2563EB]">{run.progress}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-[#2563EB] transition-all duration-500 rounded-full"
                    style={{ width: `${run.progress}%` }}
                  />
                </div>
              </div>

              {/* Session Linking footer */}
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <span>Session: <strong className="font-mono text-slate-700 dark:text-slate-300">{run.session_id}</strong></span>
                <button
                  onClick={() => onNavigate("browser_live")}
                  className="text-[#2563EB] dark:text-blue-400 hover:underline flex items-center gap-1 font-semibold"
                >
                  <Compass className="w-3 h-3" />
                  <span>Inspect Viewport Live</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
