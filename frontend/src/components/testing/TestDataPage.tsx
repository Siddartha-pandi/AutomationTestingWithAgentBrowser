"use client";

import React, { useState } from "react";
import {
  Database,
  UploadCloud,
  Download,
  Plus,
  Trash2,
  FileSpreadsheet,
  FileCode,
  Shield,
  Eye,
  EyeOff,
  Search,
  CheckCircle2,
  Save,
  RotateCcw,
  Sparkles,
  Lock,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";
import { testsApi } from "../../api";

interface TestDataPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface DatasetItem {
  id: string;
  name: string;
  description: string;
  format: "csv" | "json";
  rowCount: number;
  columns: string[];
  data: Record<string, string>[];
  lastModified: string;
}

const INITIAL_DATASETS: DatasetItem[] = [
  {
    id: "ds_users_matrix",
    name: "User Roles & Auth Test Matrix",
    description: "Parameterized test accounts covering standard RBAC permission tiers",
    format: "json",
    rowCount: 4,
    columns: ["email", "role", "expected_status", "can_publish"],
    data: [
      { email: "owner@company.local", role: "owner", expected_status: "200", can_publish: "true" },
      { email: "admin@company.local", role: "admin", expected_status: "200", can_publish: "true" },
      { email: "tester@company.local", role: "tester", expected_status: "200", can_publish: "false" },
      { email: "viewer@company.local", role: "viewer", expected_status: "200", can_publish: "false" },
    ],
    lastModified: "Today, 11:30 AM",
  },
  {
    id: "ds_referral_inputs",
    name: "Referral Form Submissions Dataset",
    description: "Synthetic test data for customer referral program stress verification",
    format: "csv",
    rowCount: 5,
    columns: ["referee_name", "program_tier", "country_code", "expected_reward"],
    data: [
      { referee_name: "Acme Logistics", program_tier: "platinum", country_code: "IN", expected_reward: "500" },
      { referee_name: "Nexus Corp", program_tier: "gold", country_code: "US", expected_reward: "250" },
      { referee_name: "FinTech Ventures", program_tier: "silver", country_code: "GB", expected_reward: "100" },
      { referee_name: "Omni Global", program_tier: "platinum", country_code: "DE", expected_reward: "500" },
      { referee_name: "Prime Analytics", program_tier: "gold", country_code: "SG", expected_reward: "250" },
    ],
    lastModified: "Today, 02:15 PM",
  },
];

export function TestDataPage({ projectId, onNavigate }: TestDataPageProps) {
  const [datasets, setDatasets] = useState<DatasetItem[]>(INITIAL_DATASETS);
  const [activeDatasetId, setActiveDatasetId] = useState<string>(INITIAL_DATASETS[0].id);
  const [search, setSearch] = useState("");
  const [maskSecrets, setMaskSecrets] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const { success, info, error } = useToast();
  const { confirm } = useConfirm();

  const activeDataset = datasets.find((d) => d.id === activeDatasetId) || datasets[0];

  // Save active dataset to PostgreSQL backend
  const handleSaveToDatabase = async () => {
    if (!activeDataset) return;
    setIsSaving(true);
    try {
      await testsApi.createDataset({
        project_id: projectId,
        name: activeDataset.name,
        description: activeDataset.description,
        format: activeDataset.format,
        headers: activeDataset.columns,
        rows: activeDataset.data,
      });
      success("Saved to Database", `Dataset '${activeDataset.name}' persisted successfully.`);
    } catch (err: any) {
      error("Save Failed", err.message || "Failed to persist dataset to database.");
    } finally {
      setIsSaving(false);
    }
  };

  // Add new row to active dataset
  const handleAddRow = () => {
    if (!activeDataset) return;
    const emptyRow: Record<string, string> = {};
    activeDataset.columns.forEach((c) => (emptyRow[c] = ""));
    const updated = {
      ...activeDataset,
      rowCount: activeDataset.rowCount + 1,
      data: [...activeDataset.data, emptyRow],
      lastModified: "Just now",
    };
    setDatasets(datasets.map((d) => (d.id === activeDataset.id ? updated : d)));
    success("Row Added", "New empty test record inserted.");
  };

  // Delete row
  const handleDeleteRow = (index: number) => {
    if (!activeDataset) return;
    const newData = activeDataset.data.filter((_, idx) => idx !== index);
    const updated = {
      ...activeDataset,
      rowCount: newData.length,
      data: newData,
      lastModified: "Just now",
    };
    setDatasets(datasets.map((d) => (d.id === activeDataset.id ? updated : d)));
  };

  // Update cell value
  const handleCellChange = (rowIndex: number, colName: string, val: string) => {
    if (!activeDataset) return;
    const updatedData = [...activeDataset.data];
    updatedData[rowIndex] = { ...updatedData[rowIndex], [colName]: val };
    const updated = {
      ...activeDataset,
      data: updatedData,
      lastModified: "Just now",
    };
    setDatasets(datasets.map((d) => (d.id === activeDataset.id ? updated : d)));
  };

  // Export CSV
  const handleExportCSV = () => {
    if (!activeDataset) return;
    const headers = activeDataset.columns.join(",");
    const rows = activeDataset.data.map((r) => activeDataset.columns.map((c) => `"${r[c] || ""}"`).join(","));
    const csvContent = [headers, ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${activeDataset.name.toLowerCase().replace(/\s+/g, "_")}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    success("Export Complete", `Exported ${activeDataset.rowCount} rows as CSV.`);
  };

  // Create new dataset
  const handleCreateDataset = () => {
    const newId = `ds_${Date.now()}`;
    const newDs: DatasetItem = {
      id: newId,
      name: "New Data-Driven Test Set",
      description: "Custom test parameters dataset",
      format: "csv",
      rowCount: 1,
      columns: ["parameter_1", "expected_value"],
      data: [{ parameter_1: "test_val", expected_value: "expected_val" }],
      lastModified: "Just now",
    };
    setDatasets([...datasets, newDs]);
    setActiveDatasetId(newId);
    success("Dataset Created", "New parameterized dataset created.");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Test Data Management
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage parameterized CSV and JSON datasets for automated data-driven testing with zero secret leaks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMaskSecrets(!maskSecrets)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-sm"
          >
            {maskSecrets ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span>{maskSecrets ? "Reveal Secrets" : "Mask Secrets"}</span>
          </button>
          <button
            onClick={handleCreateDataset}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Dataset</span>
          </button>
        </div>
      </div>

      {/* Main Workspace Layout: Datasets List (Left) + Table Editor (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left Sidebar: Datasets */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
          <div className="text-xs font-bold text-slate-400 tracking-wider uppercase px-1">
            Available Datasets ({datasets.length})
          </div>

          <div className="space-y-1.5">
            {datasets.map((ds) => (
              <button
                key={ds.id}
                onClick={() => setActiveDatasetId(ds.id)}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  activeDatasetId === ds.id
                    ? "bg-blue-50/70 dark:bg-blue-950/40 border-blue-500/50 shadow-sm"
                    : "bg-transparent border-transparent hover:bg-slate-50 dark:hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-xs text-slate-900 dark:text-white truncate">
                    {ds.name}
                  </span>
                  <span
                    className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                      ds.format === "csv"
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400"
                        : "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-400"
                    }`}
                  >
                    {ds.format}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
                  {ds.description}
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2">
                  <span>{ds.rowCount} rows</span>
                  <span>{ds.lastModified}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right Panel: Dataset Table View & Editor */}
        {activeDataset && (
          <div className="lg:col-span-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden flex flex-col">
            {/* Action Bar */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50 dark:bg-slate-950/30">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {activeDataset.name}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {activeDataset.description} &bull; {activeDataset.rowCount} rows &bull;{" "}
                  {activeDataset.columns.length} columns
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleAddRow}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 rounded-lg shadow-sm transition-colors"
                >
                  <Plus className="w-3.5 h-3.5 text-blue-600" />
                  <span>Add Row</span>
                </button>
                <button
                  onClick={handleExportCSV}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 rounded-lg shadow-sm transition-colors"
                >
                  <Download className="w-3.5 h-3.5 text-slate-500" />
                  <span>Export CSV</span>
                </button>
                <button
                  onClick={handleSaveToDatabase}
                  disabled={isSaving}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                >
                  <Save className={`w-3.5 h-3.5 ${isSaving ? "animate-spin" : ""}`} />
                  <span>{isSaving ? "Saving..." : "Save to Database"}</span>
                </button>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100/70 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2.5 px-4 w-12 text-center text-slate-400">#</th>
                    {activeDataset.columns.map((col) => (
                      <th key={col} className="py-2.5 px-4 capitalize tracking-wide font-mono text-[11px]">
                        {col}
                      </th>
                    ))}
                    <th className="py-2.5 px-4 w-16 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                  {activeDataset.data.map((row, rIdx) => (
                    <tr
                      key={rIdx}
                      className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors group"
                    >
                      <td className="py-2 px-4 text-center text-slate-400 font-mono text-[11px]">
                        {rIdx + 1}
                      </td>
                      {activeDataset.columns.map((col) => {
                        const val = row[col] || "";
                        const isSecretCol =
                          maskSecrets &&
                          (col.includes("password") ||
                            col.includes("secret") ||
                            col.includes("token") ||
                            col.includes("key"));
                        return (
                          <td key={col} className="py-1 px-3">
                            <input
                              type={isSecretCol ? "password" : "text"}
                              value={val}
                              onChange={(e) => handleCellChange(rIdx, col, e.target.value)}
                              className="w-full px-2 py-1 bg-transparent hover:bg-white dark:hover:bg-slate-800 focus:bg-white dark:focus:bg-slate-800 border border-transparent focus:border-blue-500 rounded text-slate-800 dark:text-slate-200 text-xs font-mono focus:outline-none transition-colors"
                            />
                          </td>
                        );
                      })}
                      <td className="py-1 px-4 text-right">
                        <button
                          onClick={() => handleDeleteRow(rIdx)}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                          title="Delete row"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Table Footer */}
            <div className="p-3 bg-slate-50/60 dark:bg-slate-950/40 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-emerald-500" />
                <span>Zero Secret Leak Policy: Masked values are redacted from execution logs.</span>
              </span>
              <span>Total iterations: {activeDataset.rowCount}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
