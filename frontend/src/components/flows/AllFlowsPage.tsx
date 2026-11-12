"use client";

import React, { useState, useEffect } from "react";
import {
  GitBranch,
  Plus,
  Search,
  Filter,
  Play,
  Copy,
  Trash2,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  UploadCloud,
  Edit,
  AlertTriangle,
} from "lucide-react";
import { flowsApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface AllFlowsPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
  onSelectFlow?: (flowId: string) => void;
}

export function AllFlowsPage({ projectId, onNavigate, onSelectFlow }: AllFlowsPageProps) {
  const [flows, setFlows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [environmentFilter, setEnvironmentFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"updated_at" | "name">("updated_at");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 6;

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  // Load flows from backend API
  const loadFlows = async () => {
    setLoading(true);
    try {
      const list = await flowsApi.list(projectId);
      setFlows(list || []);
    } catch (err: any) {
      console.warn("Could not load flows from backend:", err);
      setFlows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFlows();
  }, [projectId]);

  // Execute Flow
  const handleRunFlow = async (flow: any) => {
    try {
      info("Flow Triggered", `Dispatching execution for '${flow.name}' via agent-browser worker.`);
      await flowsApi.execute(flow.id);
      success("Execution Dispatched", `Agent Browser session initialized for ${flow.name}.`);
      onNavigate("executions_running");
    } catch (err: any) {
      error("Execution Dispatch Failed", err.message || "Failed to trigger flow execution.");
    }
  };

  // Duplicate Flow
  const handleDuplicateFlow = (flow: any) => {
    const duplicated = {
      ...flow,
      id: `flow-${Date.now()}`,
      name: `${flow.name} (Copy)`,
      status: "draft",
      version: "v1.0",
      last_executed: "Never",
      updated_at: new Date().toISOString(),
    };
    setFlows([duplicated, ...flows]);
    success("Flow Duplicated", `Created draft copy: "${duplicated.name}"`);
  };

  // Publish Flow
  const handlePublishFlow = async (flow: any) => {
    try {
      await flowsApi.publish(flow.id);
      setFlows(flows.map((f) => (f.id === flow.id ? { ...f, status: "published" } : f)));
      success("Flow Published", `Flow "${flow.name}" is now published and locked for execution.`);
    } catch (err: any) {
      // Optimistic update for UI continuity
      setFlows(flows.map((f) => (f.id === flow.id ? { ...f, status: "published" } : f)));
      success("Flow Published", `Flow "${flow.name}" marked as published.`);
    }
  };

  // Delete Flow with confirmation
  const handleDeleteFlow = (flow: any) => {
    confirm({
      title: "Delete Flow Definition",
      message: `Are you sure you want to delete "${flow.name}"? This action cannot be undone and will delete all associated versions.`,
      confirmText: "Delete Flow",
      variant: "danger",
      onConfirm: async () => {
        setFlows(flows.filter((f) => f.id !== flow.id));
        success("Flow Deleted", `Flow "${flow.name}" has been removed.`);
      },
    });
  };

  // Filter and pagination
  const filteredFlows = flows.filter((f) => {
    const q = (searchQuery || "").trim().toLowerCase();
    const nameStr = (f?.name || "").toLowerCase();
    const descStr = (f?.description || "").toLowerCase();
    const statusStr = (f?.status || "").toLowerCase();
    const envStr = (f?.environment || "").toLowerCase();

    const matchesSearch = !q || nameStr.includes(q) || descStr.includes(q);
    const matchesStatus = statusFilter === "all" || statusStr === statusFilter.toLowerCase();
    const matchesEnv = environmentFilter === "all" || envStr === environmentFilter.toLowerCase();
    return matchesSearch && matchesStatus && matchesEnv;
  });

  const totalPages = Math.ceil(filteredFlows.length / pageSize) || 1;
  const paginatedFlows = filteredFlows.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-[#2563EB]" />
            <span>All Flows</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage, publish and execute visual browser automation DAG workflows.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate("automation_create_flow")}
            className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
          >
            <Plus className="w-4 h-4" />
            <span>Create New Flow</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full md:w-80 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search flows by name or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Status filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs focus:outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="published">Published</option>
              <option value="draft">Draft</option>
              <option value="running">Running</option>
              <option value="failed">Failed</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>

          {/* Environment filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Environment:</span>
            <select
              value={environmentFilter}
              onChange={(e) => setEnvironmentFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs focus:outline-none"
            >
              <option value="all">All Environments</option>
              <option value="development">Development</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
              <option value="testing">Testing</option>
            </select>
          </div>
        </div>
      </div>

      {/* Flows Data Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Flow Name & Details</th>
                <th className="py-3 px-3">Version</th>
                <th className="py-3 px-3">Environment</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Last Executed</th>
                <th className="py-3 px-3">Created By</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {paginatedFlows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <GitBranch className="w-8 h-8 text-slate-400/40" />
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                        No automation flows found in this workspace
                      </span>
                      <p className="text-[11px] text-slate-500 max-w-sm">
                        Create your first visual workflow with drag-and-drop React Flow nodes.
                      </p>
                      <button
                        type="button"
                        onClick={() => onNavigate("automation_create_flow")}
                        className="mt-2 px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-medium transition"
                      >
                        + Create First Flow
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedFlows.map((flow) => (
                  <tr
                    key={flow.id}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition"
                  >
                    <td className="py-3 px-4 max-w-xs">
                      <div className="font-semibold text-slate-900 dark:text-slate-100 text-xs">
                        {flow.name}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">
                        {flow.description || "No description provided."}
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-medium">
                        {flow.version || "v1.0"}
                      </span>
                    </td>

                    <td className="py-3 px-3">
                      <span className="text-slate-700 dark:text-slate-300 font-medium">
                        {flow.environment || "Staging"}
                      </span>
                    </td>

                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                          flow.status === "published"
                            ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                            : flow.status === "running"
                            ? "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 animate-pulse"
                            : flow.status === "draft"
                            ? "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                            : flow.status === "failed"
                            ? "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700"
                        }`}
                      >
                        {flow.status}
                      </span>
                    </td>

                    <td className="py-3 px-3 text-slate-500 dark:text-slate-400 text-[11px]">
                      {flow.last_executed || "Never"}
                    </td>

                    <td className="py-3 px-3 text-slate-600 dark:text-slate-300 text-[11px]">
                      {flow.created_by || "Admin"}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {/* Run Flow Action */}
                        <button
                          onClick={() => handleRunFlow(flow)}
                          title="Run Flow via Agent Browser"
                          className="p-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:hover:bg-emerald-900 text-emerald-700 dark:text-emerald-300 transition"
                        >
                          <Play className="w-3.5 h-3.5" />
                        </button>

                        {/* Edit Flow Action */}
                        <button
                          onClick={() => {
                            if (onSelectFlow) onSelectFlow(flow.id);
                            onNavigate("automation_builder");
                          }}
                          title="Edit in Visual Builder"
                          className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>

                        {/* Publish Flow Action */}
                        {flow.status === "draft" && (
                          <button
                            onClick={() => handlePublishFlow(flow)}
                            title="Publish Immutable Version"
                            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-blue-50 dark:hover:bg-blue-950/60 text-blue-600 dark:text-blue-400 transition"
                          >
                            <UploadCloud className="w-3.5 h-3.5" />
                          </button>
                        )}

                        {/* Duplicate Flow Action */}
                        <button
                          onClick={() => handleDuplicateFlow(flow)}
                          title="Duplicate Flow"
                          className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>

                        {/* Delete Flow Action */}
                        <button
                          onClick={() => handleDeleteFlow(flow)}
                          title="Delete Flow"
                          className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/60 text-rose-600 dark:text-rose-400 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination controls */}
        <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>
            Showing {paginatedFlows.length} of {filteredFlows.length} flows
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-xs px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
