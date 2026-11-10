"use client";

import React, { useState } from "react";
import {
  ClipboardList,
  Search,
  Filter,
  Download,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  User,
  Globe,
  Lock,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface AuditLogsPageProps {
  onNavigate: (view: NavView) => void;
}

interface AuditRecord {
  id: string;
  user: string;
  action: string;
  resource: string;
  timestamp: string;
  ip_address: string;
  result: "success" | "blocked" | "warning";
  details: string;
}

export function AuditLogsPage({ onNavigate }: AuditLogsPageProps) {
  const [auditRecords, setAuditRecords] = useState<AuditRecord[]>([
    {
      id: "aud-001",
      user: "admin@company.internal",
      action: "production_execution_approved",
      resource: "Environment: Production (app.company.internal)",
      timestamp: "2026-11-10 09:14:02 IST",
      ip_address: "10.0.4.12 (Internal VPN)",
      result: "success",
      details: "Secondary confirmation granted for execution 'exec-901a'.",
    },
    {
      id: "aud-002",
      user: "dev.engineer@company.internal",
      action: "flow_published",
      resource: "Flow: Customer Onboarding (v2.1)",
      timestamp: "2026-11-10 08:30:15 IST",
      ip_address: "10.0.4.19 (Internal VPN)",
      result: "success",
      details: "Created immutable definition version with SHA-256 integrity hash.",
    },
    {
      id: "aud-003",
      user: "tester@company.internal",
      action: "unapproved_domain_blocked",
      resource: "URL: https://external-leak-test.com",
      timestamp: "2026-11-09 16:45:10 IST",
      ip_address: "10.0.4.55 (Internal VPN)",
      result: "blocked",
      details: "Subprocess adapter rejected navigation outside approved whitelist.",
    },
    {
      id: "aud-004",
      user: "admin@company.internal",
      action: "credential_created",
      resource: "Credential: Staging Lead Administrator Account",
      timestamp: "2026-11-09 11:20:00 IST",
      ip_address: "10.0.4.12 (Internal VPN)",
      result: "success",
      details: "AES-256 encrypted secret stored in private database vault.",
    },
    {
      id: "aud-005",
      user: "auditor@company.internal",
      action: "user_login",
      resource: "Session: OAuth2 Password Token",
      timestamp: "2026-11-07 14:10:00 IST",
      ip_address: "10.0.2.80 (Compliance Subnet)",
      result: "success",
      details: "Read-only auditor session initialized.",
    },
  ]);

  const [searchQuery, setSearchQuery] = useState("");
  const [resultFilter, setResultFilter] = useState("all");

  const { success } = useToast();

  const handleExportAudit = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      "ID,User,Action,Resource,Timestamp,IP Address,Result,Details\n" +
      auditRecords
        .map(
          (a) =>
            `"${a.id}","${a.user}","${a.action}","${a.resource}","${a.timestamp}","${a.ip_address}","${a.result}","${a.details}"`
        )
        .join("\n");
    const encoded = encodeURI(csvContent);
    const link = document.createElement("a");
    link.href = encoded;
    link.download = `Tamper_Resistant_Audit_Log_${Date.now()}.csv`;
    link.click();
    success("Audit Trail Exported", "Signed compliance CSV downloaded.");
  };

  const filtered = auditRecords.filter((a) => {
    const matchesSearch =
      a.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.resource.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesResult = resultFilter === "all" || a.result === resultFilter;
    return matchesSearch && matchesResult;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-[#2563EB]" />
            <span>Compliance Audit Trail</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Tamper-resistant append-only ledger tracking every login, workflow publication, and production execution.
          </p>
        </div>

        <button
          onClick={handleExportAudit}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Download className="w-4 h-4" />
          <span>Export Audit Log</span>
        </button>
      </div>

      {/* Filter and Security Tag */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search audit events by user, action, or target..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-3">
          <select
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs"
          >
            <option value="all">All Event Outcomes</option>
            <option value="success">Success</option>
            <option value="blocked">Blocked / Violation</option>
            <option value="warning">Warning</option>
          </select>

          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 text-[11px] font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Immutable Append-Only Mode</span>
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Timestamp & ID</th>
                <th className="py-3 px-3">Actor / User</th>
                <th className="py-3 px-3">Action</th>
                <th className="py-3 px-3">Target Resource</th>
                <th className="py-3 px-3">IP Address</th>
                <th className="py-3 px-3">Outcome</th>
                <th className="py-3 px-4">Audit Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-800 dark:text-slate-200 block text-xs">
                      {r.timestamp}
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">{r.id}</span>
                  </td>

                  <td className="py-3 px-3">
                    <span className="font-mono text-xs text-[#2563EB] dark:text-blue-400 font-bold">
                      {r.user}
                    </span>
                  </td>

                  <td className="py-3 px-3 font-mono text-[11px] font-semibold text-slate-800 dark:text-slate-200">
                    {r.action}
                  </td>

                  <td className="py-3 px-3 text-slate-600 dark:text-slate-300">
                    {r.resource}
                  </td>

                  <td className="py-3 px-3 font-mono text-[10px] text-slate-500">
                    {r.ip_address}
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                        r.result === "success"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : r.result === "blocked"
                          ? "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800"
                          : "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                      }`}
                    >
                      {r.result === "success" && <CheckCircle2 className="w-3 h-3" />}
                      {r.result === "blocked" && <XCircle className="w-3 h-3" />}
                      {r.result === "warning" && <AlertTriangle className="w-3 h-3" />}
                      <span>{r.result}</span>
                    </span>
                  </td>

                  <td className="py-3 px-4 text-slate-500 dark:text-slate-400 text-[11px]">
                    {r.details}
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
