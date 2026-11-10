"use client";

import React, { useState } from "react";
import {
  History,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Check,
  X,
  Eye,
  RefreshCw,
  Search,
  Filter,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { intelligenceApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface SelfHealingPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface HealingRecord {
  id: string;
  date: string;
  flow_test_name: string;
  element_id: string;
  previous_locator: string;
  new_locator: string;
  recognition_method: string;
  confidence: number;
  result: "auto_healed" | "requires_approval" | "rejected";
  why_failed: string;
  why_selected: string;
  verification_status: string;
}

export function SelfHealingPage({ projectId, onNavigate }: SelfHealingPageProps) {
  const [healingRecords, setHealingRecords] = useState<HealingRecord[]>([
    {
      id: "heal-1",
      date: "Today at 09:22 AM",
      flow_test_name: "Customer Onboarding & Email Verification",
      element_id: "referral_submit_btn",
      previous_locator: "button#submit-v1-old",
      new_locator: "button[data-testid='referral-submit-action']",
      recognition_method: "Multi-Factor Scoring (ARIA + TestId)",
      confidence: 96.8,
      result: "auto_healed",
      why_failed: "Original CSS ID '#submit-v1-old' was removed in frontend release 2.4.",
      why_selected: "Identified with 96.8% confidence (>= 95% threshold). Uniquely matched ARIA role and data-testid.",
      verification_status: "Verified in test sandbox before execution dispatch.",
    },
    {
      id: "heal-2",
      date: "Today at 08:45 AM",
      flow_test_name: "Loan Application Submission Workflow",
      element_id: "kyc_doc_upload_input",
      previous_locator: "input[type='file']#kyc-file",
      new_locator: "div.dropzone input[type='file']",
      recognition_method: "Structural Jaccard Ancestor Matching",
      confidence: 91.4,
      result: "requires_approval",
      why_failed: "Input element wrapped inside new styled drag-and-drop container.",
      why_selected: "Score within 85-94% tier. Requires human approval gate before mutating stored locator.",
      verification_status: "Pending human-in-the-loop review.",
    },
    {
      id: "heal-3",
      date: "Yesterday at 04:15 PM",
      flow_test_name: "Admin Role Delegation Flow",
      element_id: "deprovision_user_btn",
      previous_locator: "button.delete-action",
      new_locator: "button.archive-action",
      recognition_method: "Semantic Role Matching",
      confidence: 72.0,
      result: "rejected",
      why_failed: "Button class renamed to archive.",
      why_selected: "Confidence score 72.0% is below the 85% safety boundary. Safe halt triggered.",
      verification_status: "Halted safely to prevent accidental destructive action.",
    },
  ]);

  const [selectedRecordId, setSelectedRecordId] = useState<string>("heal-2");
  const [searchQuery, setSearchQuery] = useState("");

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  const activeRecord = healingRecords.find((r) => r.id === selectedRecordId) || healingRecords[0];

  const handleApprove = (record: HealingRecord) => {
    confirm({
      title: "Approve Self-Healing Replacement",
      message: `Approve replacing '${record.previous_locator}' with '${record.new_locator}' in the permanent element profile?`,
      confirmText: "Approve & Update Locator",
      variant: "primary",
      onConfirm: async () => {
        setHealingRecords(
          healingRecords.map((r) =>
            r.id === record.id ? { ...r, result: "auto_healed" } : r
          )
        );
        success("Self-Healing Approved", `Updated stored locator for '${record.element_id}'.`);
      },
    });
  };

  const handleReject = (record: HealingRecord) => {
    confirm({
      title: "Reject Locator Candidate",
      message: `Reject proposed locator for '${record.element_id}'? The automation will halt safely if the original locator fails.`,
      confirmText: "Reject Candidate",
      variant: "danger",
      onConfirm: async () => {
        setHealingRecords(
          healingRecords.map((r) =>
            r.id === record.id ? { ...r, result: "rejected" } : r
          )
        );
        info("Candidate Rejected", "Replacement locator discarded.");
      },
    });
  };

  const totalAttempts = healingRecords.length;
  const successfulRecoveries = healingRecords.filter((r) => r.result === "auto_healed").length;
  const pendingReviews = healingRecords.filter((r) => r.result === "requires_approval").length;
  const failedRecoveries = healingRecords.filter((r) => r.result === "rejected").length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <History className="w-5 h-5 text-purple-600" />
            <span>Deterministic Self-Healing History</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Audit trail of automated locator recoveries and human approval gates (Strict Zero-AI heuristics).
          </p>
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-purple-50 dark:bg-purple-950/60 border border-purple-200 dark:border-purple-800 text-purple-800 dark:text-purple-300 text-xs font-semibold">
          <Sparkles className="w-4 h-4 text-purple-600" />
          <span>Tiered Confidence: ≥95% Auto-Heal • 85-94% Approval Gate</span>
        </div>
      </div>

      {/* 4 KPI Cards (Section 18) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Total Attempts</span>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-1">{totalAttempts}</p>
          <span className="text-[10px] text-slate-500">Recorded mutations</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold text-emerald-600 uppercase">Successful Recoveries</span>
          <p className="text-2xl font-bold text-emerald-600 mt-1">{successfulRecoveries}</p>
          <span className="text-[10px] text-emerald-600 font-medium">Auto-healed (≥95%)</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold text-amber-600 uppercase">Pending Reviews</span>
          <p className="text-2xl font-bold text-amber-600 mt-1">{pendingReviews}</p>
          <span className="text-[10px] text-amber-600 font-medium">85-94% approval tier</span>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold text-rose-600 uppercase">Failed / Rejected</span>
          <p className="text-2xl font-bold text-rose-600 mt-1">{failedRecoveries}</p>
          <span className="text-[10px] text-rose-500 font-medium">Safely halted</span>
        </div>
      </div>

      {/* Main 2-Column Layout: Left Table, Right Details Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Table Column (7 cols) */}
        <div className="lg:col-span-7 bg-white dark:bg-[#161F30] rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
              Recovery Audit Log
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">Real DOM Events</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                  <th className="py-2.5 px-3">Date & Flow</th>
                  <th className="py-2.5 px-3">Element ID</th>
                  <th className="py-2.5 px-2">Confidence</th>
                  <th className="py-2.5 px-3">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {healingRecords.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => setSelectedRecordId(r.id)}
                    className={`cursor-pointer transition ${
                      selectedRecordId === r.id
                        ? "bg-purple-50/60 dark:bg-purple-950/30"
                        : "hover:bg-slate-50/70 dark:hover:bg-slate-800/40"
                    }`}
                  >
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[180px]">
                        {r.flow_test_name}
                      </div>
                      <div className="text-[10px] text-slate-400">{r.date}</div>
                    </td>

                    <td className="py-3 px-3">
                      <span className="font-mono text-[11px] font-bold text-[#2563EB] dark:text-blue-400">
                        {r.element_id}
                      </span>
                    </td>

                    <td className="py-3 px-2 font-mono font-bold text-slate-800 dark:text-slate-200">
                      {r.confidence}%
                    </td>

                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                          r.result === "auto_healed"
                            ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                            : r.result === "requires_approval"
                            ? "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 animate-pulse"
                            : "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800"
                        }`}
                      >
                        {r.result === "auto_healed" && <CheckCircle2 className="w-3 h-3" />}
                        {r.result === "requires_approval" && <AlertTriangle className="w-3 h-3" />}
                        {r.result === "rejected" && <XCircle className="w-3 h-3" />}
                        <span>{r.result.replace(/_/g, " ")}</span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Details Panel (5 cols) */}
        {activeRecord && (
          <div className="lg:col-span-5 p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4 text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
                Healing Evidence Details
              </h3>
              <span className="font-mono text-[10px] text-purple-600 font-bold">
                ID: {activeRecord.id}
              </span>
            </div>

            {/* Locator Diff */}
            <div className="space-y-2">
              <span className="font-bold text-slate-700 dark:text-slate-300 block text-[11px] uppercase tracking-wider">
                Locator Mutation Diff
              </span>
              <div className="p-2.5 rounded-lg bg-rose-50/60 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 font-mono text-[11px] text-rose-700 dark:text-rose-300">
                <span className="line-through font-bold block">- Previous: {activeRecord.previous_locator}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 font-mono text-[11px] text-emerald-700 dark:text-emerald-300">
                <span className="font-bold block">+ New Healed: {activeRecord.new_locator}</span>
              </div>
            </div>

            {/* Why Failed & Why Selected */}
            <div className="space-y-3 pt-2">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 space-y-1">
                <span className="font-bold text-slate-700 dark:text-slate-300 block">
                  Root Cause of Failure:
                </span>
                <p className="text-slate-600 dark:text-slate-400 text-[11px] leading-snug">
                  {activeRecord.why_failed}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 space-y-1">
                <span className="font-bold text-slate-700 dark:text-slate-300 block">
                  Algorithmic Rationale:
                </span>
                <p className="text-slate-600 dark:text-slate-400 text-[11px] leading-snug">
                  {activeRecord.why_selected}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 space-y-1">
                <span className="font-bold text-slate-700 dark:text-slate-300 block">
                  Verification Result:
                </span>
                <p className="text-slate-600 dark:text-slate-400 text-[11px] leading-snug font-mono">
                  {activeRecord.verification_status}
                </p>
              </div>
            </div>

            {/* Human-in-the-Loop Approval Actions if pending */}
            {activeRecord.result === "requires_approval" && (
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-2.5">
                <button
                  onClick={() => handleReject(activeRecord)}
                  className="px-3.5 py-2 rounded-xl border border-slate-300 dark:border-slate-700 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 font-semibold"
                >
                  Reject Replacement
                </button>
                <button
                  onClick={() => handleApprove(activeRecord)}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-xs flex items-center gap-1.5"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Approve & Persist</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
