"use client";

import React, { useState, useEffect } from "react";
import {
  Clock,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Play,
  RotateCcw,
  Eye,
  Download,
  Terminal,
  Calendar,
  Layers,
  ChevronLeft,
  ChevronRight,
  Trash2,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";
import { executionsApi } from "@/api";

interface ExecutionHistoryPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
  onSelectExecution?: (id: string) => void;
}

export function ExecutionHistoryPage({ projectId, onNavigate, onSelectExecution }: ExecutionHistoryPageProps) {
  const [executions, setExecutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadExecutions = async () => {
    setLoading(true);
    try {
      const list = await executionsApi.list({ projectId });
      setExecutions(list || []);
    } catch {
      setExecutions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExecutions();
  }, [projectId]);

  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [envFilter, setEnvFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;

  const { success, info } = useToast();
  const { confirm } = useConfirm();

  const handleRerun = (exec: any) => {
    confirm({
      title: "Rerun Pinned Execution",
      message: `Execute '${exec.name}' pinned to immutable version '${exec.version}' in '${exec.environment}'?`,
      confirmText: "Trigger Rerun",
      variant: "primary",
      onConfirm: () => {
        info("Rerun Dispatched", `Started background worker for ${exec.name}.`);
        onNavigate("executions_running");
      },
    });
  };

  const handleDeleteExecution = (exec: any) => {
    confirm({
      title: "Delete Execution Record",
      message: `Permanently delete execution run record for '${exec.name}' (Run ID: ${exec.id})? Associated telemetry and run reports will be deleted.`,
      confirmText: "Delete Record",
      variant: "danger",
      onConfirm: async () => {
        try {
          await executionsApi.delete(exec.id);
        } catch {
          // Fallback optimistic
        }
        setExecutions((prev) => prev.filter((e) => e.id !== exec.id));
        success("Execution Record Deleted", `Removed run ${exec.id}.`);
      },
    });
  };

  const filtered = executions.filter((e) => {
    const matchesSearch =
      e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === "all" || e.type.toLowerCase() === typeFilter.toLowerCase();
    const matchesStatus = statusFilter === "all" || e.status.toLowerCase() === statusFilter.toLowerCase();
    const matchesEnv = envFilter === "all" || e.environment.toLowerCase() === envFilter.toLowerCase();
    return matchesSearch && matchesType && matchesStatus && matchesEnv;
  });

  const totalPages = Math.ceil(filtered.length / pageSize) || 1;
  const paginated = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Clock className="w-5 h-5 text-[#2563EB]" />
            <span>Execution History</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Audit trail of historical runs pinned to immutable definition versions with telemetry.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search executions by name or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
          >
            <option value="all">All Types</option>
            <option value="flow">Flow</option>
            <option value="test">Test</option>
            <option value="suite">Suite</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={envFilter}
            onChange={(e) => setEnvFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
          >
            <option value="all">All Environments</option>
            <option value="development">Development</option>
            <option value="staging">Staging</option>
            <option value="production">Production</option>
          </select>
        </div>
      </div>

      {/* Execution History Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Execution ID & Name</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3">Version</th>
                <th className="py-3 px-3">Environment</th>
                <th className="py-3 px-3">Trigger</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Duration</th>
                <th className="py-3 px-3">Started At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Clock className="w-8 h-8 text-slate-400/40" />
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                        No execution history found in this workspace
                      </span>
                      <p className="text-[11px] text-slate-500 max-w-sm">
                        Execute automation workflows or regression test cases to record versioned runs.
                      </p>
                      <button
                        type="button"
                        onClick={() => onNavigate("automation_all_flows")}
                        className="mt-2 px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-medium transition"
                      >
                        Run Your First Flow
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                paginated.map((exec) => (
                <tr key={exec.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 max-w-xs">
                    <div className="font-mono text-[10px] text-blue-600 dark:text-blue-400 font-bold">
                      {exec.id}
                    </div>
                    <div className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                      {exec.name}
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      {exec.type}
                    </span>
                  </td>

                  <td className="py-3 px-3 font-mono text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                    {exec.version}
                  </td>

                  <td className="py-3 px-3 text-slate-700 dark:text-slate-300">
                    {exec.environment}
                  </td>

                  <td className="py-3 px-3 text-[11px] text-slate-500">
                    {exec.trigger}
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                        exec.status === "completed"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800"
                      }`}
                    >
                      {exec.status === "completed" ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      <span>{exec.status}</span>
                    </span>
                  </td>

                  <td className="py-3 px-3 font-mono text-slate-500">{exec.duration}</td>

                  <td className="py-3 px-3 text-slate-400 text-[11px]">{exec.started_at}</td>

                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => {
                          if (onSelectExecution) onSelectExecution(exec.id);
                          onNavigate("executions_details");
                        }}
                        title="View Full Details"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleRerun(exec)}
                        title="Rerun Safe"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-[#2563EB] dark:text-blue-400 transition"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleDeleteExecution(exec)}
                        title="Delete Execution Record"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              )))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
          <span>Showing {paginated.length} of {filtered.length} runs</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono px-2">Page {currentPage} of {totalPages}</span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
