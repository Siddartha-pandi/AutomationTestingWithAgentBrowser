"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Check,
  X,
  Lock,
  Users,
  KeyRound,
  FileText,
  Play,
  Save,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface RolesPermissionsPageProps {
  onNavigate: (view: NavView) => void;
}

interface PermissionRow {
  permission: string;
  description: string;
  owner: boolean;
  admin: boolean;
  developer: boolean;
  tester: boolean;
  viewer: boolean;
}

export function RolesPermissionsPage({ onNavigate }: RolesPermissionsPageProps) {
  const [matrix, setMatrix] = useState<PermissionRow[]>([
    {
      permission: "View",
      description: "Read dashboards, flows, tests, logs, reports, and DOM profiles.",
      owner: true,
      admin: true,
      developer: true,
      tester: true,
      viewer: true,
    },
    {
      permission: "Create",
      description: "Author new visual workflows, test cases, and element profiles.",
      owner: true,
      admin: true,
      developer: true,
      tester: true,
      viewer: false,
    },
    {
      permission: "Edit",
      description: "Modify existing flow DAG nodes, test assertions, and schedules.",
      owner: true,
      admin: true,
      developer: true,
      tester: false,
      viewer: false,
    },
    {
      permission: "Delete",
      description: "Permanently delete flows, test cases, and screenshots.",
      owner: true,
      admin: true,
      developer: false,
      tester: false,
      viewer: false,
    },
    {
      permission: "Execute",
      description: "Dispatch on-demand workflow runs to Agent Browser workers.",
      owner: true,
      admin: true,
      developer: true,
      tester: true,
      viewer: false,
    },
    {
      permission: "Publish",
      description: "Promote draft flows to immutable release versions with checksums.",
      owner: true,
      admin: true,
      developer: true,
      tester: false,
      viewer: false,
    },
    {
      permission: "Manage Users",
      description: "Invite, deactivate, and assign RBAC roles to team members.",
      owner: true,
      admin: true,
      developer: false,
      tester: false,
      viewer: false,
    },
    {
      permission: "Manage Credentials",
      description: "Create and update AES-256 encrypted credential vault secrets.",
      owner: true,
      admin: true,
      developer: false,
      tester: false,
      viewer: false,
    },
  ]);

  const { success } = useToast();

  const handleSaveMatrix = () => {
    success("Permissions Persisted", "RBAC policy synchronized with FastAPI backend enforcement.");
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#2563EB]" />
            <span>Roles & Permissions Matrix</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Role-Based Access Control (RBAC) enforced at FastAPI middleware and database layers.
          </p>
        </div>

        <button
          onClick={handleSaveMatrix}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Save className="w-4 h-4" />
          <span>Save Permissions Policy</span>
        </button>
      </div>

      {/* Role Descriptions Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 text-xs space-y-1">
          <span className="font-bold text-purple-900 dark:text-purple-300">Owner</span>
          <p className="text-[11px] text-purple-700 dark:text-purple-400">
            Unrestricted access across all workspace tenant settings and billing.
          </p>
        </div>
        <div className="p-3.5 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 text-xs space-y-1">
          <span className="font-bold text-blue-900 dark:text-blue-300">Admin</span>
          <p className="text-[11px] text-blue-700 dark:text-blue-400">
            User management, credentials vault, and system configuration.
          </p>
        </div>
        <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs space-y-1">
          <span className="font-bold text-emerald-900 dark:text-emerald-300">Developer</span>
          <p className="text-[11px] text-emerald-700 dark:text-emerald-400">
            Author, edit, publish and execute visual flows and test cases.
          </p>
        </div>
        <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs space-y-1">
          <span className="font-bold text-amber-900 dark:text-amber-300">Tester</span>
          <p className="text-[11px] text-amber-700 dark:text-amber-400">
            Create tests, dispatch executions, and analyze test report trends.
          </p>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs space-y-1">
          <span className="font-bold text-slate-800 dark:text-slate-200">Viewer</span>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            Strict read-only compliance access for auditors and reviewers.
          </p>
        </div>
      </div>

      {/* Permission Matrix Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Permission Capability</th>
                <th className="py-3 px-3 text-center">Owner</th>
                <th className="py-3 px-3 text-center">Admin</th>
                <th className="py-3 px-3 text-center">Developer</th>
                <th className="py-3 px-3 text-center">Tester</th>
                <th className="py-3 px-3 text-center">Viewer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {matrix.map((row, idx) => (
                <tr key={row.permission} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                  <td className="py-3.5 px-4 max-w-xs">
                    <span className="font-bold text-slate-900 dark:text-slate-100 text-xs">
                      {row.permission}
                    </span>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      {row.description}
                    </p>
                  </td>

                  {/* Owner */}
                  <td className="py-3.5 px-3 text-center">
                    <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 inline-flex items-center justify-center">
                      <Check className="w-3.5 h-3.5" />
                    </span>
                  </td>

                  {/* Admin */}
                  <td className="py-3.5 px-3 text-center">
                    {row.admin ? (
                      <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 inline-flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </span>
                    ) : (
                      <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 inline-flex items-center justify-center">
                        <X className="w-3.5 h-3.5" />
                      </span>
                    )}
                  </td>

                  {/* Developer */}
                  <td className="py-3.5 px-3 text-center">
                    {row.developer ? (
                      <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 inline-flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </span>
                    ) : (
                      <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 inline-flex items-center justify-center">
                        <X className="w-3.5 h-3.5" />
                      </span>
                    )}
                  </td>

                  {/* Tester */}
                  <td className="py-3.5 px-3 text-center">
                    {row.tester ? (
                      <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 inline-flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </span>
                    ) : (
                      <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 inline-flex items-center justify-center">
                        <X className="w-3.5 h-3.5" />
                      </span>
                    )}
                  </td>

                  {/* Viewer */}
                  <td className="py-3.5 px-3 text-center">
                    {row.viewer ? (
                      <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-600 inline-flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </span>
                    ) : (
                      <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 inline-flex items-center justify-center">
                        <X className="w-3.5 h-3.5" />
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
