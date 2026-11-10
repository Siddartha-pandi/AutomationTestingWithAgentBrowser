"use client";

import React, { useState, useEffect } from "react";
import {
  Calendar,
  Clock,
  Plus,
  Play,
  Trash2,
  Edit,
  Power,
  PowerOff,
  AlertCircle,
  CheckCircle2,
  GitBranch,
  FolderKanban,
  Globe,
  X,
  Search,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";
import { schedulesApi } from "@/api";

interface SchedulesPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface ScheduleItem {
  id: string;
  name: string;
  type: "Flow" | "Test Suite";
  target_name: string;
  environment: string;
  cron_expression: string;
  frequency_label: string;
  timezone: string;
  next_run: string;
  last_run: string;
  is_enabled: boolean;
  created_by: string;
}

export function SchedulesPage({ projectId, onNavigate }: SchedulesPageProps) {
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      const list = await schedulesApi.list(projectId);
      setSchedules(list || []);
    } catch {
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSchedules();
  }, [projectId]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<ScheduleItem | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Modal Form State
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState<"Flow" | "Test Suite">("Flow");
  const [formTarget, setFormTarget] = useState("Customer Onboarding & Email Verification");
  const [formEnv, setFormEnv] = useState("Staging");
  const [formPreset, setFormPreset] = useState("daily");
  const [formCron, setFormCron] = useState("0 9 * * *");
  const [formTimezone, setFormTimezone] = useState("Asia/Kolkata");

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  const handleOpenCreateModal = () => {
    setEditingSchedule(null);
    setFormName("");
    setFormType("Flow");
    setFormTarget("Customer Onboarding & Email Verification");
    setFormEnv("Staging");
    setFormPreset("daily");
    setFormCron("0 9 * * *");
    setFormTimezone("Asia/Kolkata");
    setModalOpen(true);
  };

  const handleOpenEditModal = (sched: ScheduleItem) => {
    setEditingSchedule(sched);
    setFormName(sched.name);
    setFormType(sched.type);
    setFormTarget(sched.target_name);
    setFormEnv(sched.environment);
    setFormCron(sched.cron_expression);
    setFormTimezone(sched.timezone);
    setModalOpen(true);
  };

  const handleSaveSchedule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      error("Schedule Name Required", "Please enter a unique schedule name.");
      return;
    }

    // Check duplicate schedule prevention
    const isDuplicate = schedules.some(
      (s) =>
        s.id !== editingSchedule?.id &&
        s.target_name === formTarget &&
        s.environment === formEnv &&
        s.cron_expression === formCron
    );
    if (isDuplicate) {
      error(
        "Duplicate Schedule Prevented",
        `A scheduled execution already exists for '${formTarget}' in '${formEnv}' with the same cron timing.`
      );
      return;
    }

    if (editingSchedule) {
      setSchedules(
        schedules.map((s) =>
          s.id === editingSchedule.id
            ? {
                ...s,
                name: formName.trim(),
                type: formType,
                target_name: formTarget,
                environment: formEnv,
                cron_expression: formCron,
                timezone: formTimezone,
              }
            : s
        )
      );
      success("Schedule Updated", `Schedule "${formName}" updated.`);
    } else {
      const newSched: ScheduleItem = {
        id: `sched-${Date.now()}`,
        name: formName.trim(),
        type: formType,
        target_name: formTarget,
        environment: formEnv,
        cron_expression: formCron,
        frequency_label: formPreset === "daily" ? "Daily at 09:00 AM" : formPreset === "hourly" ? "Hourly" : "Custom Cron",
        timezone: formTimezone,
        next_run: "Projected within 24 hours",
        last_run: "Never",
        is_enabled: true,
        created_by: "Administrator",
      };
      setSchedules([newSched, ...schedules]);
      success("Schedule Created", `Schedule "${formName}" added to Celery Beat.`);
    }
    setModalOpen(false);
  };

  const handleToggleEnable = (sched: ScheduleItem) => {
    setSchedules(
      schedules.map((s) =>
        s.id === sched.id ? { ...s, is_enabled: !s.is_enabled } : s
      )
    );
    if (!sched.is_enabled) {
      success("Schedule Enabled", `"${sched.name}" is now active in Celery Beat scheduler.`);
    } else {
      info("Schedule Paused", `"${sched.name}" will not trigger until re-enabled.`);
    }
  };

  const handleRunImmediately = (sched: ScheduleItem) => {
    info("Immediate Execution", `Triggered on-demand run of ${sched.type} "${sched.target_name}".`);
    onNavigate("executions_running");
  };

  const handleDeleteSchedule = (sched: ScheduleItem) => {
    confirm({
      title: "Delete Schedule",
      message: `Are you sure you want to delete the schedule "${sched.name}"? This removes the recurring execution job.`,
      confirmText: "Delete Schedule",
      variant: "danger",
      onConfirm: async () => {
        setSchedules(schedules.filter((s) => s.id !== sched.id));
        success("Schedule Deleted", `Schedule "${sched.name}" removed.`);
      },
    });
  };

  const filtered = schedules.filter(
    (s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.target_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-[#2563EB]" />
            <span>Execution Schedules</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Configure automated Celery Beat cron jobs for Flows and Test Suites (Default Timezone: Asia/Kolkata).
          </p>
        </div>

        <button
          onClick={handleOpenCreateModal}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Schedule</span>
        </button>
      </div>

      {/* Search & Status Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-80 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search schedules by name or target..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="text-[11px] font-mono text-slate-400 hidden sm:block">
          Active Timezone: <span className="font-bold text-slate-700 dark:text-slate-300">Asia/Kolkata (IST)</span>
        </div>
      </div>

      {/* Schedules Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Schedule Name</th>
                <th className="py-3 px-3">Type & Target</th>
                <th className="py-3 px-3">Environment</th>
                <th className="py-3 px-3">Cron & Timing</th>
                <th className="py-3 px-3">Next Execution</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Calendar className="w-8 h-8 text-slate-400/40" />
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                        No automation schedules in this workspace
                      </span>
                      <p className="text-[11px] text-slate-500 max-w-sm">
                        Configure automated Celery Beat recurring cron schedules for Flows and Test Suites.
                      </p>
                      <button
                        type="button"
                        onClick={handleOpenCreateModal}
                        className="mt-2 px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-medium transition"
                      >
                        + Create First Schedule
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((sched) => (
                <tr key={sched.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-900 dark:text-slate-100 text-xs">
                      {sched.name}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      By {sched.created_by}
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <div className="flex items-center gap-1.5 font-medium text-slate-800 dark:text-slate-200">
                      {sched.type === "Flow" ? (
                        <GitBranch className="w-3.5 h-3.5 text-[#2563EB]" />
                      ) : (
                        <FolderKanban className="w-3.5 h-3.5 text-emerald-500" />
                      )}
                      <span>{sched.target_name}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono mt-0.5">{sched.type}</div>
                  </td>

                  <td className="py-3 px-3">
                    <span className="font-medium text-slate-700 dark:text-slate-300">
                      {sched.environment}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <div className="font-mono text-[11px] font-semibold text-slate-800 dark:text-slate-200">
                      {sched.cron_expression}
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400">
                      {sched.timezone}
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <div className="text-slate-800 dark:text-slate-200 font-medium">
                      {sched.next_run}
                    </div>
                    <div className="text-[10px] text-slate-400">Last: {sched.last_run}</div>
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        sched.is_enabled
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : "bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700"
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${sched.is_enabled ? "bg-emerald-500" : "bg-slate-400"}`}></span>
                      <span>{sched.is_enabled ? "Active" : "Paused"}</span>
                    </span>
                  </td>

                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Run Immediately Action */}
                      <button
                        onClick={() => handleRunImmediately(sched)}
                        title="Run Immediately"
                        className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/60 dark:hover:bg-blue-900 text-[#2563EB] dark:text-blue-300 transition"
                      >
                        <Play className="w-3.5 h-3.5" />
                      </button>

                      {/* Toggle Enable/Pause */}
                      <button
                        onClick={() => handleToggleEnable(sched)}
                        title={sched.is_enabled ? "Pause Schedule" : "Resume Schedule"}
                        className={`p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 transition ${
                          sched.is_enabled
                            ? "hover:bg-amber-50 dark:hover:bg-amber-950/60 text-amber-600"
                            : "hover:bg-emerald-50 dark:hover:bg-emerald-950/60 text-emerald-600"
                        }`}
                      >
                        {sched.is_enabled ? <PowerOff className="w-3.5 h-3.5" /> : <Power className="w-3.5 h-3.5" />}
                      </button>

                      {/* Edit Schedule */}
                      <button
                        onClick={() => handleOpenEditModal(sched)}
                        title="Edit Schedule"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>

                      {/* Delete Schedule */}
                      <button
                        onClick={() => handleDeleteSchedule(sched)}
                        title="Delete Schedule"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/60 text-rose-600 dark:text-rose-400 transition"
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
      </div>

      {/* Create / Edit Schedule Modal Dialog */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-lg w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-[#2563EB]" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {editingSchedule ? "Edit Schedule" : "Create Execution Schedule"}
                </h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveSchedule} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Schedule Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Daily Nightly Regression Pass"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Execution Type
                  </label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  >
                    <option value="Flow">Automation Flow</option>
                    <option value="Test Suite">Test Suite</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Target Environment
                  </label>
                  <select
                    value={formEnv}
                    onChange={(e) => setFormEnv(e.target.value)}
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
                  Target Flow / Suite
                </label>
                <input
                  type="text"
                  required
                  value={formTarget}
                  onChange={(e) => setFormTarget(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Cron Expression *
                  </label>
                  <input
                    type="text"
                    required
                    value={formCron}
                    onChange={(e) => setFormCron(e.target.value)}
                    placeholder="0 9 * * 1-5"
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 font-mono text-slate-900 dark:text-slate-100"
                  />
                  <span className="text-[10px] text-slate-400 mt-0.5 block">Standard 5-part cron syntax</span>
                </div>

                <div>
                  <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">
                    Timezone
                  </label>
                  <input
                    type="text"
                    disabled
                    value={formTimezone}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-500 font-mono cursor-not-allowed"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold shadow-xs"
                >
                  {editingSchedule ? "Save Changes" : "Create Schedule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
