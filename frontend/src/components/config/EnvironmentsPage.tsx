"use client";

import React, { useState } from "react";
import {
  Globe,
  Plus,
  ShieldAlert,
  ShieldCheck,
  Lock,
  Edit,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  X,
  ExternalLink,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface EnvironmentsPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface EnvironmentItem {
  id: string;
  name: "Development" | "Testing" | "Staging" | "Production" | string;
  base_url: string;
  description: string;
  status: "healthy" | "degraded" | "guarded";
  allowed_domains: string[];
  is_production: boolean;
  variables: Record<string, string>;
}

export function EnvironmentsPage({ projectId, onNavigate }: EnvironmentsPageProps) {
  const [environments, setEnvironments] = useState<EnvironmentItem[]>([
    {
      id: "env-dev",
      name: "Development",
      base_url: "http://127.0.0.1:3000",
      description: "Local development server and mock APIs.",
      status: "healthy",
      allowed_domains: ["localhost", "127.0.0.1"],
      is_production: false,
      variables: { API_PORT: "8000", MOCK_AUTH: "true" },
    },
    {
      id: "env-test",
      name: "Testing",
      base_url: "https://qa.internal.company.net",
      description: "QA automated regression server with seeded synthetic test databases.",
      status: "healthy",
      allowed_domains: ["qa.internal.company.net", "auth.internal.company.net"],
      is_production: false,
      variables: { TEST_SUITE_CONCURRENCY: "4" },
    },
    {
      id: "env-staging",
      name: "Staging",
      base_url: "https://staging.internal.company.net",
      description: "Pre-release staging replica with production-identical configurations.",
      status: "healthy",
      allowed_domains: ["staging.internal.company.net", "auth.internal.company.net"],
      is_production: false,
      variables: { GATEWAY_TIMEOUT: "30" },
    },
    {
      id: "env-prod",
      name: "Production",
      base_url: "https://app.company.internal",
      description: "Guarded live production environment. Strict secondary confirmation required for all runs.",
      status: "guarded",
      allowed_domains: ["app.company.internal", "sso.company.internal"],
      is_production: true,
      variables: { STRICT_AUDIT: "true", ENFORCE_2FA: "true" },
    },
  ]);

  const [modalOpen, setModalOpen] = useState(false);
  const [nameInput, setNameInput] = useState("Custom Pre-Prod");
  const [urlInput, setUrlInput] = useState("https://preprod.company.internal");
  const [descInput, setDescInput] = useState("");
  const [isProdInput, setIsProdInput] = useState(false);

  const { success, warning, info } = useToast();
  const { confirm } = useConfirm();

  const handleCreateEnvironment = (e: React.FormEvent) => {
    e.preventDefault();
    const newEnv: EnvironmentItem = {
      id: `env-${Date.now()}`,
      name: nameInput.trim(),
      base_url: urlInput.trim(),
      description: descInput.trim() || "Custom environment configuration.",
      status: isProdInput ? "guarded" : "healthy",
      allowed_domains: [urlInput.replace(/^https?:\/\//, "").split("/")[0]],
      is_production: isProdInput,
      variables: {},
    };

    setEnvironments([...environments, newEnv]);
    setModalOpen(false);
    success("Environment Added", `Configured '${nameInput}' with domain whitelisting.`);
  };

  const handleTestTriggerInEnv = (env: EnvironmentItem) => {
    if (env.is_production) {
      confirm({
        title: "CONFIRM PRODUCTION EXECUTION",
        message: "You are attempting to execute an automated workflow against the LIVE PRODUCTION environment. This will interact with production data and external systems.",
        confirmText: "I Acknowledge & Authorize Production Run",
        variant: "danger",
        onConfirm: () => {
          warning("Production Run Authorized", "Dispatched execution to production queue with strict audit logging.");
          onNavigate("executions_running");
        },
      });
    } else {
      info("Triggered", `Dispatched execution in ${env.name}.`);
      onNavigate("executions_running");
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Globe className="w-5 h-5 text-emerald-500" />
            <span>Environment Management</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Configure target tiers, security domain restriction whitelists, and production execution guards.
          </p>
        </div>

        <button
          onClick={() => {
            setNameInput("Custom Sandbox");
            setUrlInput("https://sandbox.company.internal");
            setDescInput("");
            setIsProdInput(false);
            setModalOpen(true);
          }}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Environment</span>
        </button>
      </div>

      {/* Environments Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {environments.map((env) => (
          <div
            key={env.id}
            className={`p-5 rounded-2xl bg-white dark:bg-[#161F30] border shadow-2xs space-y-4 transition ${
              env.is_production
                ? "border-amber-300 dark:border-amber-900/60 ring-1 ring-amber-400/20"
                : "border-slate-200 dark:border-slate-800"
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                    {env.name}
                  </h3>
                  {env.is_production && (
                    <span className="text-[10px] px-2 py-0.2 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 font-bold border border-amber-300 dark:border-amber-800 flex items-center gap-1">
                      <Lock className="w-3 h-3" />
                      <span>Production Guarded</span>
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                  {env.description}
                </p>
              </div>

              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-semibold capitalize ${
                  env.status === "healthy"
                    ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                    : "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                }`}
              >
                {env.status}
              </span>
            </div>

            {/* Base URL & Domain Whitelist */}
            <div className="space-y-2 text-xs pt-3 border-t border-slate-100 dark:border-slate-800">
              <div className="flex items-center justify-between text-slate-700 dark:text-slate-300">
                <span className="text-slate-400 font-medium">Base URL:</span>
                <span className="font-mono text-[11px] font-bold">{env.base_url}</span>
              </div>
              <div className="space-y-1">
                <span className="text-slate-400 font-medium text-[10px] uppercase">
                  Allowed Domain Whitelist ({env.allowed_domains.length}):
                </span>
                <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                  {env.allowed_domains.map((dom) => (
                    <span
                      key={dom}
                      className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                    >
                      {dom}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Actions Bar */}
            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
              <button
                onClick={() => handleTestTriggerInEnv(env)}
                className={`px-3 py-1.5 rounded-lg text-white font-semibold transition shadow-xs ${
                  env.is_production
                    ? "bg-amber-600 hover:bg-amber-700"
                    : "bg-[#2563EB] hover:bg-blue-600"
                }`}
              >
                {env.is_production ? "Test with Confirmation" : "Run Workflow Here"}
              </button>

              <span className="text-[10px] text-slate-400 font-mono">
                {Object.keys(env.variables).length} Config Vars
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Globe className="w-4 h-4 text-emerald-500" />
                <span>Create Environment</span>
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateEnvironment} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Name *</label>
                <input
                  type="text"
                  required
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Base URL *</label>
                <input
                  type="url"
                  required
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Description</label>
                <textarea
                  rows={2}
                  value={descInput}
                  onChange={(e) => setDescInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 resize-none"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={isProdInput}
                  onChange={(e) => setIsProdInput(e.target.checked)}
                  className="rounded text-amber-600"
                />
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  Mark as Production (Enforces Confirmation Gate)
                </span>
              </label>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold shadow-xs"
                >
                  Save Environment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
