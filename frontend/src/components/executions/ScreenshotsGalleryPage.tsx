"use client";

import React, { useState } from "react";
import {
  Image as ImageIcon,
  Search,
  Filter,
  Grid,
  List,
  Download,
  Trash2,
  Eye,
  X,
  Calendar,
  Layers,
  Globe,
  Camera,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface ScreenshotsGalleryPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface ScreenshotItem {
  id: string;
  name: string;
  execution_id: string;
  step_name: string;
  timestamp: string;
  environment: string;
  size_kb: number;
  url: string;
}

export function ScreenshotsGalleryPage({ projectId, onNavigate }: ScreenshotsGalleryPageProps) {
  const [screenshots, setScreenshots] = useState<ScreenshotItem[]>([]);

  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedScreenshot, setSelectedScreenshot] = useState<ScreenshotItem | null>(null);

  const { success } = useToast();
  const { confirm } = useConfirm();

  const handleDownload = (sc: ScreenshotItem) => {
    const link = document.createElement("a");
    link.href = sc.url;
    link.download = sc.name;
    link.click();
    success("Download Started", `Saving '${sc.name}'.`);
  };

  const handleDelete = (sc: ScreenshotItem) => {
    confirm({
      title: "Delete Screenshot",
      message: `Permanently delete screenshot '${sc.name}' from storage?`,
      confirmText: "Delete",
      variant: "danger",
      onConfirm: () => {
        setScreenshots(screenshots.filter((s) => s.id !== sc.id));
        success("Screenshot Deleted", "Artifact removed from private storage.");
      },
    });
  };

  const filtered = screenshots.filter((s) => {
    const q = (searchQuery || "").trim().toLowerCase();
    if (!q) return true;
    const nameStr = (s?.name || "").toLowerCase();
    const execStr = (s?.execution_id || "").toLowerCase();
    const stepStr = (s?.step_name || "").toLowerCase();
    return nameStr.includes(q) || execStr.includes(q) || stepStr.includes(q);
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-[#2563EB]" />
            <span>Screenshots Gallery</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Compliant visual artifacts captured during browser automation and test assertion runs.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 flex items-center gap-1">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-lg transition ${
                viewMode === "grid"
                  ? "bg-blue-50 dark:bg-blue-950/60 text-[#2563EB]"
                  : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              }`}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`p-1.5 rounded-lg transition ${
                viewMode === "list"
                  ? "bg-blue-50 dark:bg-blue-950/60 text-[#2563EB]"
                  : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              }`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Search Toolbar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="text"
            placeholder="Search by screenshot, execution ID or step..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs focus:outline-none"
          />
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          {filtered.length} screenshots stored
        </span>
      </div>

      {/* Gallery Grid View */}
      {viewMode === "grid" ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((sc) => (
            <div
              key={sc.id}
              className="p-3.5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-3 group hover:border-blue-500 transition"
            >
              <div
                onClick={() => setSelectedScreenshot(sc)}
                className="aspect-video bg-slate-950 rounded-xl overflow-hidden cursor-pointer relative flex items-center justify-center"
              >
                <img
                  src={sc.url}
                  alt={sc.name}
                  className="w-full h-full object-contain group-hover:scale-105 transition"
                />
                <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                  <span className="px-3 py-1.5 rounded-lg bg-white/90 text-slate-900 font-bold text-xs flex items-center gap-1 shadow-md">
                    <Eye className="w-3.5 h-3.5" />
                    <span>View Lightbox</span>
                  </span>
                </div>
              </div>

              <div className="space-y-1 text-xs">
                <div className="font-bold text-slate-900 dark:text-slate-100 truncate">
                  {sc.name}
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                  {sc.step_name}
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 font-mono">
                  <span>{sc.execution_id} • {sc.environment}</span>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleDownload(sc)}
                      className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      title="Download"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(sc)}
                      className="p-1 rounded hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 transition"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Gallery List View */
        <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Screenshot Name</th>
                <th className="py-3 px-3">Execution ID</th>
                <th className="py-3 px-3">Step Name</th>
                <th className="py-3 px-3">Environment</th>
                <th className="py-3 px-3">Timestamp</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.map((sc) => (
                <tr key={sc.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                  <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">{sc.name}</td>
                  <td className="py-3 px-3 font-mono text-[#2563EB]">{sc.execution_id}</td>
                  <td className="py-3 px-3 text-slate-600 dark:text-slate-300">{sc.step_name}</td>
                  <td className="py-3 px-3">{sc.environment}</td>
                  <td className="py-3 px-3 text-slate-400">{sc.timestamp}</td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => setSelectedScreenshot(sc)}
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDownload(sc)}
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                        title="Download"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(sc)}
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-600 transition"
                        title="Delete"
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
      )}

      {/* Lightbox Modal */}
      {selectedScreenshot && (
        <div
          onClick={() => setSelectedScreenshot(null)}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-sm cursor-zoom-out animate-in fade-in duration-150"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-slate-900 rounded-2xl max-w-4xl w-full p-4 border border-slate-800 space-y-3 cursor-default"
          >
            <div className="flex items-center justify-between text-white text-xs pb-2 border-b border-slate-800">
              <span className="font-bold">{selectedScreenshot.name}</span>
              <button
                onClick={() => setSelectedScreenshot(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <img src={selectedScreenshot.url} alt={selectedScreenshot.name} className="w-full max-h-[70vh] object-contain rounded-lg" />
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800 font-mono">
              <span>{selectedScreenshot.step_name} • {selectedScreenshot.environment}</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const toDelete = selectedScreenshot;
                    setSelectedScreenshot(null);
                    handleDelete(toDelete);
                  }}
                  className="px-3 py-1 rounded-lg border border-rose-500/30 hover:bg-rose-500/20 text-rose-400 font-semibold flex items-center gap-1.5 transition"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete</span>
                </button>
                <button
                  onClick={() => handleDownload(selectedScreenshot)}
                  className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center gap-1.5 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
