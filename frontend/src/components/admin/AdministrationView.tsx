"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  ShieldAlert,
  ClipboardList,
  CheckCircle2,
  XCircle,
  UserPlus,
  ShieldCheck,
  Lock,
} from "lucide-react";
import { adminApi } from "@/api";

interface AdministrationViewProps {
  initialSubTab?: "users" | "roles" | "audit";
}

export function AdministrationView({ initialSubTab = "users" }: AdministrationViewProps) {
  const [activeTab, setActiveTab] = useState<"users" | "roles" | "audit">(initialSubTab);

  // Users State
  const [users, setUsers] = useState<any[]>([]);
  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [uList, aList] = await Promise.allSettled([
        adminApi.listUsers(),
        adminApi.listAuditLogs(),
      ]);
      if (uList.status === "fulfilled" && uList.value) {
        setUsers(
          uList.value.map((u: any) => ({
            id: String(u.id),
            email: u.email,
            full_name: u.full_name || u.email.split("@")[0],
            role: u.roles && u.roles[0]?.name
              ? (u.roles[0].name.charAt(0).toUpperCase() + u.roles[0].name.slice(1))
              : "Viewer",
            status: u.is_active ? "active" : "inactive",
            last_login: "Recent",
          }))
        );
      }
      if (aList.status === "fulfilled" && aList.value) {
        setAuditLogs(
          aList.value.map((a: any) => ({
            id: String(a.id || `aud-${Math.random()}`),
            timestamp: a.timestamp || a.created_at || "Recent",
            user: a.user_email || a.user_id || "system",
            action: (a.action || "AUDIT_EVENT").toUpperCase(),
            resource: a.resource_type ? `${a.resource_type}:${a.resource_id || ""}` : a.resource || "system",
            status: a.result?.toUpperCase() || "SUCCESS",
            ip: a.client_ip || a.ip || "127.0.0.1",
          }))
        );
      }
    } catch {
      // offline/no data
    } finally {
      setLoading(false);
    }
  };

  // Roles Matrix (Section 13 of Master Prompt)
  const roles = [
    {
      name: "Owner",
      description: "Full access across all projects, environments, users, and audit logs.",
      permissions: [
        "All Permissions",
        "Manage Users & Roles",
        "Manage Environments",
        "Create, Edit & Publish Flows",
        "Create & Execute Tests",
        "Approve Self-Healing",
        "Audit Log Inspection",
      ],
      badgeColor: "bg-purple-100 text-purple-800 border-purple-200",
    },
    {
      name: "Admin",
      description: "Manage users, environments, credentials, and system configuration.",
      permissions: [
        "Manage Users & Roles",
        "Manage Environments & Credentials",
        "Publish Flows & Tests",
        "Approve Self-Healing",
        "Audit Log Inspection",
      ],
      badgeColor: "bg-blue-100 text-blue-800 border-blue-200",
    },
    {
      name: "Developer",
      description: "Create, edit, debug, and publish flows and automated test suites.",
      permissions: [
        "Create & Edit Flows",
        "Publish Flow Versions",
        "Create & Edit Tests",
        "Execute Flows & Tests",
        "Inspect DOM & Live Browser",
      ],
      badgeColor: "bg-emerald-100 text-emerald-800 border-emerald-200",
    },
    {
      name: "Tester",
      description: "Create tests, trigger execution runs, and view execution reports.",
      permissions: [
        "Create Test Cases",
        "Execute Tests & Test Suites",
        "View Execution Reports & Screenshots",
        "Inspect Logs",
      ],
      badgeColor: "bg-amber-100 text-amber-800 border-amber-200",
    },
    {
      name: "Viewer",
      description: "Read-only access to executions, test reports, and flow graphs.",
      permissions: [
        "View Flows (Read-Only)",
        "View Tests (Read-Only)",
        "View Execution Reports & Logs",
      ],
      badgeColor: "bg-slate-100 text-slate-800 border-slate-200",
    },
  ];



  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header & Tabs */}
      <div className="border-b border-slate-200 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Administration & Security</h2>
          <p className="text-xs text-slate-500">
            Multi-user role-based access control (RBAC) and immutable compliance audit trails.
          </p>
        </div>

        <div className="flex items-center p-1 bg-slate-200/60 rounded-lg text-xs font-medium">
          <button
            onClick={() => setActiveTab("users")}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${
              activeTab === "users"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Users</span>
          </button>

          <button
            onClick={() => setActiveTab("roles")}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${
              activeTab === "roles"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Roles & Permissions</span>
          </button>

          <button
            onClick={() => setActiveTab("audit")}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition ${
              activeTab === "audit"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <ClipboardList className="w-3.5 h-3.5" />
            <span>Audit Logs</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Users */}
      {activeTab === "users" && (
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900 text-sm">Registered Accounts ({users.length})</h3>
            <button className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs flex items-center gap-1.5 shadow-sm transition">
              <UserPlus className="w-3.5 h-3.5" />
              <span>Invite User</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 border-y border-slate-200 uppercase text-[10px] font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Full Name</th>
                  <th className="py-2.5 px-3">Email Address</th>
                  <th className="py-2.5 px-3">Assigned Role</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Last Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/60 transition">
                    <td className="py-2.5 px-3 font-medium text-slate-800">{u.full_name}</td>
                    <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">{u.email}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded font-medium text-[11px] bg-slate-100 text-slate-700 border border-slate-200">
                        {u.role}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>Active</span>
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">{u.last_login}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Roles & Permissions */}
      {activeTab === "roles" && (
        <div className="space-y-4">
          <p className="text-xs text-slate-600">
            Strict role-based authorization matrix enforced on all backend API endpoints and UI views.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {roles.map((r) => (
              <div key={r.name} className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-slate-900 text-sm">{r.name}</h4>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${r.badgeColor}`}>
                    {r.name} Tier
                  </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{r.description}</p>
                <div className="pt-2 border-t border-slate-100 space-y-1.5">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Granted Permissions:
                  </span>
                  {r.permissions.map((perm) => (
                    <div key={perm} className="text-xs text-slate-700 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span>{perm}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Audit Logs */}
      {activeTab === "audit" && (
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">Security & Compliance Audit Trail</h3>
              <p className="text-xs text-slate-500">
                Immutable record of all workflow modifications, execution runs, approval responses, and access events.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 border-y border-slate-200 uppercase text-[10px] font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Actor / Principal</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Target Resource</th>
                  <th className="py-2.5 px-3">Outcome</th>
                  <th className="py-2.5 px-3">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/60 transition">
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                      {log.timestamp}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 font-medium">{log.user}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-blue-700 font-semibold">
                      {log.action}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 font-mono text-[11px]">{log.resource}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {log.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400 font-mono text-[11px]">{log.ip}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

