"use client";

import React, { useState } from "react";
import {
  GitBranch,
  ArrowLeft,
  Plus,
  Save,
  Tag,
  Layers,
  Globe,
  FileText,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";
import { flowsApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface CreateFlowPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
  onFlowCreated?: (flowId: string) => void;
}

export function CreateFlowPage({ projectId, onNavigate, onFlowCreated }: CreateFlowPageProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [environment, setEnvironment] = useState("Staging");
  const [tagsInput, setTagsInput] = useState("smoke, regression, onboarding");
  const [loading, setLoading] = useState(false);

  const { success, error } = useToast();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      error("Flow Name Required", "Please provide a descriptive name for your automation flow.");
      return;
    }

    setLoading(true);
    try {
      const initialDefinition = {
        nodes: [
          {
            id: "node_start",
            type: "actionNode",
            position: { x: 250, y: 50 },
            data: {
              action: "navigate",
              summary: "Navigate to base application",
              config: {
                url: "https://example.com/login",
                timeout: 30,
              },
            },
          },
          {
            id: "node_click",
            type: "actionNode",
            position: { x: 250, y: 180 },
            data: {
              action: "click",
              summary: "Click submit or primary action",
              config: {
                logical_id: "login_submit_btn",
                recognition_strategy: "deterministic_multi_factor",
                timeout: 15,
                retry_policy: "exponential_backoff",
              },
            },
          },
        ],
        edges: [
          {
            id: "edge_start_to_click",
            source: "node_start",
            target: "node_click",
            animated: true,
          },
        ],
      };

      const res = await flowsApi.create({
        project_id: projectId,
        name: name.trim(),
        description: description.trim(),
        definition: initialDefinition,
      });

      success("Flow Created Successfully", `"${name}" is ready for visual DAG design.`);
      const newId = res?.id || `flow-${Date.now()}`;
      if (onFlowCreated) onFlowCreated(newId);
      onNavigate("automation_builder");
    } catch (err: any) {
      error("Creation Failed", err.message || "Failed to create flow definition in backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate("automation_all_flows")}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-[#2563EB]" />
              <span>Create New Automation Flow</span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Initialize an enterprise visual flow and configure execution targets.
            </p>
          </div>
        </div>
      </div>

      {/* Main Creation Form Card */}
      <div className="p-6 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-6">
        <form onSubmit={handleCreate} className="space-y-5">
          {/* Flow Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <span>Flow Name</span>
              <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. User Signup & KYC Verification Pipeline"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-[11px] text-slate-400">
              A distinctive enterprise title for this browser automation DAG.
            </p>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
              Description & Objectives
            </label>
            <textarea
              rows={3}
              placeholder="Specify the target workflows, required credentials, and expected outcomes..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {/* Project & Environment Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Project */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-[#2563EB]" />
                <span>Assigned Project</span>
              </label>
              <select
                disabled
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs cursor-not-allowed"
              >
                <option>Enterprise QA Suite (Active Workspace)</option>
              </select>
            </div>

            {/* Target Environment */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-emerald-500" />
                <span>Target Environment</span>
              </label>
              <select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Development">Development (Localhost / Sandbox)</option>
                <option value="Testing">Testing (QA Server)</option>
                <option value="Staging">Staging (Pre-Release)</option>
                <option value="Production">Production (Guarded Live)</option>
              </select>
            </div>
          </div>

          {/* Tags */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-purple-500" />
              <span>Categorization Tags</span>
            </label>
            <input
              type="text"
              placeholder="e.g. smoke, regression, onboarding, payment"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-[11px] text-slate-400">
              Comma-separated labels for grouping, scheduling and test matrix filtering.
            </p>
          </div>

          {/* Zero-AI Compliance Note */}
          <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300 flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <span className="font-bold">Deterministic Flow Guarantee:</span>
              <p className="text-[11px] text-emerald-700 dark:text-emerald-400">
                This workflow will be compiled to a strictly deterministic Directed Acyclic Graph (DAG) executed by the local `agent-browser` engine without any AI generation or external API leaks.
              </p>
            </div>
          </div>

          {/* Form Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => onNavigate("automation_all_flows")}
              className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-2 shadow-xs transition disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{loading ? "Creating..." : "Create Flow & Open Builder"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
