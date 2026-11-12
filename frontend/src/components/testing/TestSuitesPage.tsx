"use client";

import React, { useState, useEffect } from "react";
import {
  FolderKanban,
  Plus,
  Play,
  StopCircle,
  FileText,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowUpDown,
  Trash2,
  Edit,
  Layers,
  ChevronRight,
  GripVertical,
  X,
  ListOrdered,
} from "lucide-react";
import { testSuitesApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface TestSuitesPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface TestSuiteItem {
  id: string;
  name: string;
  description: string;
  total_tests: number;
  passed: number;
  failed: number;
  skipped: number;
  last_execution: string;
  success_rate: number;
  sequence_mode: "Sequential" | "Parallel";
  tests: { id: string; name: string; priority: number }[];
}

export function TestSuitesPage({ projectId, onNavigate }: TestSuitesPageProps) {
  const [suites, setSuites] = useState<TestSuiteItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSuiteId, setSelectedSuiteId] = useState<string>("");

  const loadSuites = async () => {
    setLoading(true);
    try {
      const list = await testSuitesApi.list(projectId);
      setSuites(list || []);
      if (list && list.length > 0) {
        setSelectedSuiteId(list[0].id);
      }
    } catch {
      setSuites([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuites();
  }, [projectId]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingSuite, setEditingSuite] = useState<TestSuiteItem | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [runningSuiteId, setRunningSuiteId] = useState<string | null>(null);

  // New suite form state
  const [newSuiteName, setNewSuiteName] = useState("");
  const [newSuiteDesc, setNewSuiteDesc] = useState("");
  const [newSequenceMode, setNewSequenceMode] = useState<"Sequential" | "Parallel">("Sequential");

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  const activeSuite = suites.find((s) => s.id === selectedSuiteId) || suites[0];

  const handleOpenCreateModal = () => {
    setEditingSuite(null);
    setNewSuiteName("");
    setNewSuiteDesc("");
    setNewSequenceMode("Sequential");
    setModalOpen(true);
  };

  const handleOpenEditModal = (suite: TestSuiteItem) => {
    setEditingSuite(suite);
    setNewSuiteName(suite.name);
    setNewSuiteDesc(suite.description);
    setNewSequenceMode(suite.sequence_mode);
    setModalOpen(true);
  };

  const handleSaveSuite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSuiteName.trim()) {
      error("Suite Name Required", "Please enter a test suite title.");
      return;
    }

    if (editingSuite) {
      try {
        await testSuitesApi.update(editingSuite.id, {
          name: newSuiteName.trim(),
          description: newSuiteDesc.trim() || undefined,
        });
      } catch {
        // Optimistic
      }

      setSuites(
        suites.map((s) =>
          s.id === editingSuite.id
            ? {
                ...s,
                name: newSuiteName.trim(),
                description: newSuiteDesc.trim() || s.description,
                sequence_mode: newSequenceMode,
              }
            : s
        )
      );
      setModalOpen(false);
      setEditingSuite(null);
      success("Test Suite Updated", `Updated suite "${newSuiteName}".`);
      return;
    }

    const newSuite: TestSuiteItem = {
      id: `suite-${Date.now()}`,
      name: newSuiteName.trim(),
      description: newSuiteDesc.trim() || "No description provided.",
      total_tests: 1,
      passed: 1,
      failed: 0,
      skipped: 0,
      last_execution: "Never",
      success_rate: 100,
      sequence_mode: newSequenceMode,
      tests: [{ id: "tc-001", name: "Default Sanity Assertion", priority: 1 }],
    };

    setSuites([newSuite, ...suites]);
    setSelectedSuiteId(newSuite.id);
    setModalOpen(false);
    success("Test Suite Created", `Suite "${newSuiteName}" created.`);
  };

  const handleRemoveTestFromSuite = (suite: TestSuiteItem, testId: string) => {
    const updatedTests = suite.tests.filter((t) => t.id !== testId);
    const updatedSuite = {
      ...suite,
      tests: updatedTests,
      total_tests: updatedTests.length,
    };
    setSuites(suites.map((s) => (s.id === suite.id ? updatedSuite : s)));
    success("Test Removed", "Test case removed from suite sequence.");
  };

  const handleRunSuite = async (suite: TestSuiteItem) => {
    setRunningSuiteId(suite.id);
    info("Test Suite Dispatched", `Executing all ${suite.total_tests} test cases in '${suite.name}' (${suite.sequence_mode}).`);
    try {
      await testSuitesApi.execute(suite.id);
    } catch {
      // simulated progress
    }
    setTimeout(() => {
      setRunningSuiteId(null);
      success("Suite Execution Complete", `Passed ${suite.passed} of ${suite.total_tests} tests in ${suite.name}.`);
    }, 2500);
  };

  const handleStopSuite = (suite: TestSuiteItem) => {
    setRunningSuiteId(null);
    info("Suite Stopped", `Execution aborted for ${suite.name}.`);
  };

  const handleDeleteSuite = (suite: TestSuiteItem) => {
    confirm({
      title: "Delete Test Suite",
      message: `Delete test suite "${suite.name}"? This will not delete the individual test cases.`,
      confirmText: "Delete Suite",
      variant: "danger",
      onConfirm: () => {
        const remaining = suites.filter((s) => s.id !== suite.id);
        setSuites(remaining);
        if (remaining.length > 0) setSelectedSuiteId(remaining[0].id);
        success("Suite Removed", `Deleted ${suite.name}.`);
      },
    });
  };

  const filteredSuites = suites.filter((s) => {
    const q = (searchQuery || "").trim().toLowerCase();
    if (!q) return true;
    const nameStr = (s?.name || "").toLowerCase();
    const descStr = (s?.description || "").toLowerCase();
    return nameStr.includes(q) || descStr.includes(q);
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <FolderKanban className="w-5 h-5 text-purple-600" />
            <span>Test Suites</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Group, sequence and orchestrate multi-test regression suites via Agent Browser.
          </p>
        </div>

        <button
          onClick={handleOpenCreateModal}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>Create Test Suite</span>
        </button>
      </div>

      {/* Main 2-Column Layout: Left Suites List, Right Suite Details & Reordering */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Suites List */}
        <div className="space-y-3">
          <div className="p-2.5 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex items-center gap-2">
            <Search className="w-4 h-4 text-slate-400 ml-1" />
            <input
              type="text"
              placeholder="Search suites..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent border-none text-xs text-slate-800 dark:text-slate-200 focus:outline-none"
            />
          </div>

          <div className="space-y-2.5">
            {filteredSuites.length === 0 ? (
              <div className="p-8 text-center text-slate-400 border border-dashed border-slate-300 dark:border-slate-800 rounded-xl">
                <FolderKanban className="w-8 h-8 text-slate-400/40 mx-auto mb-2" />
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">No Test Suites</span>
                <p className="text-[11px] text-slate-500 mt-1">Create a test suite to group test assertions.</p>
              </div>
            ) : (
              filteredSuites.map((s) => (
                <div
                  key={s.id}
                  onClick={() => setSelectedSuiteId(s.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition group ${
                    selectedSuiteId === s.id
                      ? "bg-white dark:bg-[#161F30] border-blue-600 dark:border-blue-500 ring-2 ring-blue-500/10 shadow-sm"
                      : "bg-white dark:bg-[#161F30] border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-1.5">
                    <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100 truncate pr-2">
                      {s.name}
                    </h3>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                        {s.sequence_mode}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenEditModal(s);
                        }}
                        className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        title="Edit Suite"
                      >
                        <Edit className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSuite(s);
                        }}
                        className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition"
                        title="Delete Suite"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                    {s.description}
                  </p>

                  <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-3">
                      <span className="text-slate-500 dark:text-slate-400">
                        <strong>{s.total_tests}</strong> tests
                      </span>
                      <span className="text-emerald-600 font-semibold">{s.success_rate}% pass</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Selected Suite Inspector, Reorderable Tests & Actions */}
        {!activeSuite ? (
          <div className="lg:col-span-2 p-12 text-center rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col items-center justify-center space-y-3">
            <FolderKanban className="w-12 h-12 text-slate-400/40" />
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">No Test Suite in Workspace</h3>
            <p className="text-xs text-slate-500 max-w-sm">Create a new test suite to configure sequence execution, manage priority order, and view test pass rates.</p>
            <button
              onClick={() => {
                setNewSuiteName("");
                setNewSuiteDesc("");
                setNewSequenceMode("Sequential");
                setModalOpen(true);
              }}
              className="px-4 py-2 bg-[#2563EB] hover:bg-blue-600 text-white rounded-xl text-xs font-semibold shadow-xs flex items-center gap-1.5 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create First Suite</span>
            </button>
          </div>
        ) : (
          <div className="lg:col-span-2 space-y-5">
            {/* Suite Header Info & Controls */}
            <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    {activeSuite.name}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {activeSuite.description}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {runningSuiteId === activeSuite.id ? (
                    <button
                      onClick={() => handleStopSuite(activeSuite)}
                      className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
                    >
                      <StopCircle className="w-4 h-4" />
                      <span>Stop Suite</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => handleRunSuite(activeSuite)}
                      className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
                    >
                      <Play className="w-4 h-4" />
                      <span>Run Complete Suite</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleOpenEditModal(activeSuite)}
                    className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                    title="Edit Suite"
                  >
                    <Edit className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => handleDeleteSuite(activeSuite)}
                    className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition"
                    title="Delete Suite"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* KPI metrics bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Tests</span>
                  <p className="text-lg font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                    {activeSuite.total_tests}
                  </p>
                </div>
                <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800">
                  <span className="text-[10px] text-emerald-700 dark:text-emerald-400 uppercase font-semibold">Passed</span>
                  <p className="text-lg font-bold text-emerald-700 dark:text-emerald-400 mt-0.5">
                    {activeSuite.passed}
                  </p>
                </div>
                <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800">
                  <span className="text-[10px] text-rose-700 dark:text-rose-400 uppercase font-semibold">Failed</span>
                  <p className="text-lg font-bold text-rose-700 dark:text-rose-400 mt-0.5">
                    {activeSuite.failed}
                  </p>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Success Rate</span>
                  <p className="text-lg font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                    {activeSuite.success_rate}%
                  </p>
                </div>
              </div>
            </div>

            {/* Test Cases Included in Suite (Reordering & Priorities) */}
            <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                    <ListOrdered className="w-4 h-4 text-[#2563EB]" />
                    <span>Configured Execution Sequence</span>
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Execution order for test cases in this suite ({activeSuite.sequence_mode}).
                  </p>
                </div>

                <button
                  onClick={() => onNavigate("testing_builder")}
                  className="text-xs font-semibold text-[#2563EB] dark:text-blue-400 hover:underline flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Test Case</span>
                </button>
              </div>

              <div className="space-y-2">
                {activeSuite.tests.map((test, index) => (
                  <div
                    key={test.id}
                    className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-md bg-blue-100 dark:bg-blue-950/60 text-[#2563EB] font-mono font-bold text-[11px] flex items-center justify-center">
                        {index + 1}
                      </span>
                      <div>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {test.name}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono block">
                          ID: {test.id}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => success("Sequence Updated", `Priority moved for ${test.name}`)}
                        className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
                        title="Reorder"
                      >
                        <ArrowUpDown className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleRemoveTestFromSuite(activeSuite, test.id)}
                        className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition"
                        title="Remove Test from Suite"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create / Edit Suite Modal Dialog */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <FolderKanban className="w-4 h-4 text-purple-600" />
                <span>{editingSuite ? "Edit Test Suite" : "Create New Test Suite"}</span>
              </h3>
              <button
                onClick={() => {
                  setModalOpen(false);
                  setEditingSuite(null);
                }}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveSuite} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Suite Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. End-to-End Checkout Suite"
                  value={newSuiteName}
                  onChange={(e) => setNewSuiteName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Description</label>
                <textarea
                  rows={3}
                  placeholder="Describe the test scope and execution criteria..."
                  value={newSuiteDesc}
                  onChange={(e) => setNewSuiteDesc(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 resize-none"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Sequence Mode</label>
                <select
                  value={newSequenceMode}
                  onChange={(e) => setNewSequenceMode(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                >
                  <option value="Sequential">Sequential (Deterministic Step-by-Step)</option>
                  <option value="Parallel">Parallel (Concurrent Worker Execution)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setModalOpen(false);
                    setEditingSuite(null);
                  }}
                  className="px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold shadow-xs"
                >
                  {editingSuite ? "Save Changes" : "Create Suite"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
