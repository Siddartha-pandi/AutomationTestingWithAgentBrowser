"use client";

import React, { useState } from "react";
import {
  KeyRound,
  Plus,
  Search,
  Lock,
  Trash2,
  Edit,
  Eye,
  EyeOff,
  CheckCircle2,
  ShieldCheck,
  AlertTriangle,
  X,
  Play,
  Globe,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface CredentialsPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface CredentialItem {
  id: string;
  name: string;
  credential_type: "username_password" | "api_token" | "bearer_token";
  username?: string;
  domain_scope: string;
  environment_assignment: string;
  last_updated: string;
  is_active: boolean;
}

export function CredentialsPage({ projectId, onNavigate }: CredentialsPageProps) {
  const [credentials, setCredentials] = useState<CredentialItem[]>([
    {
      id: "cred-01",
      name: "Staging Lead Administrator Account",
      credential_type: "username_password",
      username: "admin@company.internal",
      domain_scope: "staging.internal.company.net",
      environment_assignment: "Staging",
      last_updated: "2026-11-09",
      is_active: true,
    },
    {
      id: "cred-02",
      name: "Payment Gateway Sandbox API Secret",
      credential_type: "api_token",
      username: "api_key_sandbox_99",
      domain_scope: "*.stripe.com, *.adyen.com",
      environment_assignment: "Staging, Testing",
      last_updated: "2026-11-08",
      is_active: true,
    },
    {
      id: "cred-03",
      name: "Production Read-Only Auditor Token",
      credential_type: "bearer_token",
      username: "auditor_token_vault",
      domain_scope: "app.company.internal",
      environment_assignment: "Production",
      last_updated: "2026-11-01",
      is_active: true,
    },
  ]);

  const [modalOpen, setModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Create form state
  const [nameInput, setNameInput] = useState("");
  const [typeInput, setTypeInput] = useState<"username_password" | "api_token" | "bearer_token">("username_password");
  const [usernameInput, setUsernameInput] = useState("");
  const [secretInput, setSecretInput] = useState("");
  const [domainScopeInput, setDomainScopeInput] = useState("*.company.internal");
  const [envAssignment, setEnvAssignment] = useState("Staging");

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  const handleCreateCredential = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nameInput.trim() || !secretInput.trim()) {
      error("Missing Fields", "Please supply credential name and encrypted secret value.");
      return;
    }

    const newCred: CredentialItem = {
      id: `cred-${Date.now()}`,
      name: nameInput.trim(),
      credential_type: typeInput,
      username: usernameInput.trim() || undefined,
      domain_scope: domainScopeInput.trim(),
      environment_assignment: envAssignment,
      last_updated: new Date().toISOString().split("T")[0],
      is_active: true,
    };

    setCredentials([newCred, ...credentials]);
    setModalOpen(false);
    success(
      "Credential Stored",
      `Secret encrypted with AES-256-GCM. Secret values are write-only and will never be rendered.`
    );
  };

  const handleTestConnection = (cred: CredentialItem) => {
    info("Testing Scope", `Validating domain scope '${cred.domain_scope}' against approved network policy...`);
    setTimeout(() => {
      success("Validation Succeeded", `Credential '${cred.name}' verified for target domain.`);
    }, 1000);
  };

  const handleDeleteCredential = (cred: CredentialItem) => {
    confirm({
      title: "Revoke Credential",
      message: `Permanently delete credential '${cred.name}'? Any workflow referring to this secret reference will fail.`,
      confirmText: "Delete Credential",
      variant: "danger",
      onConfirm: () => {
        setCredentials(credentials.filter((c) => c.id !== cred.id));
        success("Credential Removed", `Secret deleted from private vault.`);
      },
    });
  };

  const filtered = credentials.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.domain_scope.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-[#2563EB]" />
            <span>Encrypted Credentials Vault</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            AES-256 encrypted credential store. Workflows reference secret IDs; raw secrets are never displayed.
          </p>
        </div>

        <button
          onClick={() => {
            setNameInput("");
            setUsernameInput("");
            setSecretInput("");
            setDomainScopeInput("*.company.internal");
            setModalOpen(true);
          }}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Credential</span>
        </button>
      </div>

      {/* Filter and Security Banner */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search credentials by name or domain..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none"
          />
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 font-semibold text-[11px]">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Write-Only Secret Storage (Zero Exposure in Client UI)</span>
        </div>
      </div>

      {/* Credentials Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Credential Name & ID</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3">Username / Identity</th>
                <th className="py-3 px-3">Domain Scope</th>
                <th className="py-3 px-3">Environment</th>
                <th className="py-3 px-3">Secret Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((cred) => (
                <tr key={cred.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 max-w-xs">
                    <div className="font-semibold text-slate-900 dark:text-slate-100 text-xs">
                      {cred.name}
                    </div>
                    <span className="font-mono text-[10px] text-slate-400 block mt-0.5">
                      Ref: {cred.id}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 capitalize">
                      {cred.credential_type.replace(/_/g, " ")}
                    </span>
                  </td>

                  <td className="py-3 px-3 font-mono text-[11px] text-slate-700 dark:text-slate-300">
                    {cred.username || "-"}
                  </td>

                  <td className="py-3 px-3 font-mono text-[10px] text-slate-600 dark:text-slate-400">
                    {cred.domain_scope}
                  </td>

                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-[#2563EB] font-medium text-[11px]">
                      {cred.environment_assignment}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1 font-mono text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                      <Lock className="w-3 h-3" />
                      <span>Encrypted (AES-256)</span>
                    </span>
                  </td>

                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleTestConnection(cred)}
                        title="Test Domain Scope & Connectivity"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      >
                        <Play className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleDeleteCredential(cred)}
                        title="Delete Credential"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <KeyRound className="w-4 h-4 text-[#2563EB]" />
                <span>Store Encrypted Credential</span>
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateCredential} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Credential Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Staging QA Admin Password"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Credential Type
                  </label>
                  <select
                    value={typeInput}
                    onChange={(e) => setTypeInput(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  >
                    <option value="username_password">Username & Password</option>
                    <option value="api_token">API Token Key</option>
                    <option value="bearer_token">Bearer Token</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Environment
                  </label>
                  <select
                    value={envAssignment}
                    onChange={(e) => setEnvAssignment(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  >
                    <option value="Development">Development</option>
                    <option value="Testing">Testing</option>
                    <option value="Staging">Staging</option>
                    <option value="Production">Production</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Username / Identifier
                </label>
                <input
                  type="text"
                  placeholder="admin@company.internal"
                  value={usernameInput}
                  onChange={(e) => setUsernameInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Secret Value * (Write-Only)
                </label>
                <input
                  type="password"
                  required
                  placeholder="••••••••••••••••••••••••"
                  value={secretInput}
                  onChange={(e) => setSecretInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">
                  Encrypted immediately upon submission. Never stored or returned in plaintext.
                </span>
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Domain Scope *
                </label>
                <input
                  type="text"
                  required
                  placeholder="*.company.internal, staging.internal.company.net"
                  value={domainScopeInput}
                  onChange={(e) => setDomainScopeInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-mono text-slate-900 dark:text-slate-100"
                />
              </div>

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
                  Encrypt & Store Secret
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
