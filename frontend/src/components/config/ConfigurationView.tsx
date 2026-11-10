"use client";

import React, { useState } from "react";
import {
  Layers,
  Globe,
  KeyRound,
  Sliders,
  ShieldCheck,
  Plus,
  Save,
  CheckCircle2,
  Trash2,
  Eye,
  EyeOff,
  Lock,
} from "lucide-react";
import { NavView } from "@/components/layout/AppShell";

interface ConfigurationViewProps {
  initialSubTab?: "projects" | "environments" | "credentials" | "browser";
}

export function ConfigurationView({ initialSubTab = "projects" }: ConfigurationViewProps) {
  const [activeTab, setActiveTab] = useState<"projects" | "environments" | "credentials" | "browser">(
    initialSubTab
  );

  // Projects State
  const [projects, setProjects] = useState([
    {
      id: "p1-company-portal",
      name: "Acme Customer Portal",
      description: "Primary customer facing loan & referral automation workflows",
      active: true,
      created_at: "2026-11-01",
    },
    {
      id: "p2-internal-ops",
      name: "Internal Ops & Backoffice",
      description: "Automated underwriting, verification & approval pipelines",
      active: false,
      created_at: "2026-11-05",
    },
  ]);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");

  // Environments State
  const [environments, setEnvironments] = useState([
    {
      id: "env-staging",
      name: "Staging",
      baseUrl: "https://staging.internal.company.net",
      isDefault: true,
      allowedDomains: ["staging.internal.company.net", "auth.internal.company.net"],
    },
    {
      id: "env-prod",
      name: "Production",
      baseUrl: "https://app.company.net",
      isDefault: false,
      allowedDomains: ["app.company.net"],
    },
  ]);

  // Credentials State
  const [credentials, setCredentials] = useState([
    {
      id: "cred-admin-user",
      keyName: "APP_ADMIN_CREDENTIALS",
      username: "ops.admin@company.net",
      maskedSecret: "••••••••••••••••",
      env: "Staging",
      lastRotated: "2026-11-08",
    },
    {
      id: "cred-test-partner",
      keyName: "TEST_PARTNER_API_KEY",
      username: "partner_sandbox_491",
      maskedSecret: "••••••••••••••••",
      env: "Staging",
      lastRotated: "2026-11-09",
    },
  ]);

  // Browser Settings State
  const [browserConfig, setBrowserConfig] = useState({
    viewportWidth: 1280,
    viewportHeight: 800,
    headless: true,
    navigationTimeoutSeconds: 30,
    actionTimeoutSeconds: 15,
    maxRetries: 0,
    strictDomainIsolation: true,
    blockExternalAiTraffic: true,
    userAgent: "AutomationTestingWithAgentBrowser/1.0 (agent-browser engine)",
  });
  const [savedSuccess, setSavedSuccess] = useState(false);

  function handleSaveBrowserSettings() {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  }

  function handleAddProject() {
    if (!newProjectName.trim()) return;
    const newProj = {
      id: `p-${Date.now().toString(36)}`,
      name: newProjectName.trim(),
      description: newProjectDesc.trim() || "Workspace project",
      active: false,
      created_at: new Date().toISOString().split("T")[0],
    };
    setProjects([...projects, newProj]);
    setNewProjectName("");
    setNewProjectDesc("");
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Configuration Header & Tabs */}
      <div className="border-b border-slate-200 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">System Configuration</h2>
          <p className="text-xs text-slate-500">
            Manage projects, execution environments, secure secret vaults, and browser engine isolation.
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex items-center p-1 bg-slate-200/60 rounded-lg text-xs font-medium">
          <button
            onClick={() => setActiveTab("projects")}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${
              activeTab === "projects"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Projects</span>
          </button>

          <button
            onClick={() => setActiveTab("environments")}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${
              activeTab === "environments"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Environments</span>
          </button>

          <button
            onClick={() => setActiveTab("credentials")}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${
              activeTab === "credentials"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Credentials Vault</span>
          </button>

          <button
            onClick={() => setActiveTab("browser")}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${
              activeTab === "browser"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Browser Settings</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Projects */}
      {activeTab === "projects" && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-semibold text-slate-900 text-sm">Add New Project</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-medium text-slate-700 block mb-1">Project Name</label>
                <input
                  type="text"
                  placeholder="e.g. Core Banking System"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="font-medium text-slate-700 block mb-1">Description</label>
                <input
                  type="text"
                  placeholder="Scope & automation objectives"
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
            <button
              onClick={handleAddProject}
              className="px-3.5 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs flex items-center gap-1.5 transition shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Project</span>
            </button>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
            <h3 className="font-semibold text-slate-900 text-sm">Active Projects ({projects.length})</h3>
            <div className="divide-y divide-slate-100">
              {projects.map((proj) => (
                <div key={proj.id} className="py-3 flex items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900 text-xs">{proj.name}</span>
                      {proj.active && (
                        <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-mono text-[10px] border border-blue-200 font-medium">
                          Active Selection
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{proj.description}</p>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5">ID: {proj.id} • Created {proj.created_at}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {!proj.active && (
                      <button
                        onClick={() => {
                          setProjects(projects.map((p) => ({ ...p, active: p.id === proj.id })));
                        }}
                        className="px-2.5 py-1 rounded border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition"
                      >
                        Switch To
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Environments */}
      {activeTab === "environments" && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900 text-sm">Deployment Environments</h3>
                <p className="text-xs text-slate-500">
                  Configure base URLs and domain allowlists for SSRF prevention.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {environments.map((env) => (
                <div key={env.id} className="p-4 rounded-lg border border-slate-200 space-y-2 bg-slate-50/50">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-800 text-xs">{env.name}</span>
                    {env.isDefault && (
                      <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] border border-emerald-200 font-medium">
                        Default
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-600 font-mono bg-white p-2 rounded border border-slate-200 truncate">
                    {env.baseUrl}
                  </div>
                  <div className="text-[11px] text-slate-500 space-y-1">
                    <span className="font-medium text-slate-600">Allowed Domains:</span>
                    <div className="flex flex-wrap gap-1">
                      {env.allowedDomains.map((dom) => (
                        <span key={dom} className="px-1.5 py-0.5 rounded bg-slate-200/70 text-slate-700 font-mono text-[10px]">
                          {dom}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Credentials */}
      {activeTab === "credentials" && (
        <div className="space-y-6">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-900 text-sm">Encrypted Credentials Vault</h3>
                <p className="text-xs text-slate-500">
                  Zero secrets are ever logged or included in DOM snapshots. Masked at all output layers.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 border-y border-slate-200 uppercase text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Key Name</th>
                    <th className="py-2.5 px-3">Identifier / Username</th>
                    <th className="py-2.5 px-3">Secret Value</th>
                    <th className="py-2.5 px-3">Environment</th>
                    <th className="py-2.5 px-3">Last Rotated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {credentials.map((cred) => (
                    <tr key={cred.id}>
                      <td className="py-2.5 px-3 font-mono font-semibold text-blue-700">{cred.keyName}</td>
                      <td className="py-2.5 px-3 text-slate-700">{cred.username}</td>
                      <td className="py-2.5 px-3 font-mono text-slate-400 flex items-center gap-2">
                        <span>{cred.maskedSecret}</span>
                        <Lock className="w-3 h-3 text-slate-400" />
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">{cred.env}</td>
                      <td className="py-2.5 px-3 text-slate-400">{cred.lastRotated}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Browser Settings */}
      {activeTab === "browser" && (
        <div className="p-5 rounded-xl bg-white border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">Agent Browser Runtime Settings</h3>
              <p className="text-xs text-slate-500">
                Configure agent-browser CLI execution parameters and company security sandboxing.
              </p>
            </div>
            <button
              onClick={handleSaveBrowserSettings}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs flex items-center gap-1.5 transition shadow-sm"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Configuration</span>
            </button>
          </div>

          {savedSuccess && (
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Browser runtime configuration saved successfully.</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="font-medium text-slate-700 block mb-1">Viewport Width (px)</label>
              <input
                type="number"
                value={browserConfig.viewportWidth}
                onChange={(e) =>
                  setBrowserConfig({ ...browserConfig, viewportWidth: Number(e.target.value) })
                }
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800"
              />
            </div>

            <div>
              <label className="font-medium text-slate-700 block mb-1">Viewport Height (px)</label>
              <input
                type="number"
                value={browserConfig.viewportHeight}
                onChange={(e) =>
                  setBrowserConfig({ ...browserConfig, viewportHeight: Number(e.target.value) })
                }
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800"
              />
            </div>

            <div>
              <label className="font-medium text-slate-700 block mb-1">Navigation Timeout (Seconds)</label>
              <input
                type="number"
                value={browserConfig.navigationTimeoutSeconds}
                onChange={(e) =>
                  setBrowserConfig({ ...browserConfig, navigationTimeoutSeconds: Number(e.target.value) })
                }
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800"
              />
            </div>

            <div>
              <label className="font-medium text-slate-700 block mb-1">Action Timeout (Seconds)</label>
              <input
                type="number"
                value={browserConfig.actionTimeoutSeconds}
                onChange={(e) =>
                  setBrowserConfig({ ...browserConfig, actionTimeoutSeconds: Number(e.target.value) })
                }
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-slate-800"
              />
            </div>
          </div>

          {/* Security & Isolation Controls */}
          <div className="pt-3 border-t border-slate-100 space-y-3">
            <h4 className="font-semibold text-slate-800 text-xs">Security & Isolation Policies</h4>

            <label className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50/50 cursor-pointer">
              <input
                type="checkbox"
                checked={browserConfig.strictDomainIsolation}
                onChange={(e) =>
                  setBrowserConfig({ ...browserConfig, strictDomainIsolation: e.target.checked })
                }
                className="w-4 h-4 rounded text-blue-600"
              />
              <div className="text-xs">
                <span className="font-medium text-slate-800 block">Strict Domain Isolation & SSRF Prevention</span>
                <span className="text-slate-500 text-[11px]">
                  Blocks browser navigation to private IP ranges (127.0.0.1, 10.x, 192.168.x) and unapproved hosts.
                </span>
              </div>
            </label>

            <label className="flex items-center gap-3 p-3 rounded-lg border border-emerald-200 bg-emerald-50/40 cursor-pointer">
              <input
                type="checkbox"
                checked={browserConfig.blockExternalAiTraffic}
                readOnly
                className="w-4 h-4 rounded text-emerald-600"
              />
              <div className="text-xs">
                <span className="font-semibold text-emerald-950 block">Mandatory Zero-AI Policy Enforcement</span>
                <span className="text-emerald-800 text-[11px]">
                  Permanently disallows all outbound connections to AI inference endpoints (OpenAI, Anthropic, Gemini, Ollama). Hardcoded active.
                </span>
              </div>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}

