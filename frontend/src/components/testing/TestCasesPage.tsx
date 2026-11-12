"use client";

import React, { useState, useEffect } from "react";
import {
  CheckSquare,
  Plus,
  Search,
  Play,
  Copy,
  Trash2,
  Edit,
  Clock,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  MinusCircle,
  FileCode,
  FolderKanban,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { testsApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface TestCasesPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
  onSelectTest?: (testId: string) => void;
}

export function TestCasesPage({ projectId, onNavigate, onSelectTest }: TestCasesPageProps) {
  const [tests, setTests] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTests();
  }, [projectId]);

  const loadTests = async () => {
    setLoading(true);
    try {
      const list = await testsApi.list(projectId);
      setTests(list || []);
    } catch (err: any) {
      console.warn("Could not load tests from backend:", err);
      setTests([]);
    } finally {
      setLoading(false);
    }
  };

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [suiteFilter, setSuiteFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;

  const { success, error, info } = useToast();
  const { confirm } = useConfirm();

  // Run single test
  const handleRunTest = async (test: any) => {
    try {
      info("Test Dispatched", `Running test '${test.name}' via Agent Browser test runner.`);
      await testsApi.execute(test.id);
      success("Test Execution Started", `Session active for ${test.test_id}.`);
      onNavigate("executions_running");
    } catch (err: any) {
      error("Execution Failed", err.message || "Could not dispatch test execution.");
    }
  };

  // Duplicate test
  const handleDuplicateTest = (test: any) => {
    const duplicated = {
      ...test,
      id: `tc-${Date.now()}`,
      test_id: `${test.test_id}-COPY`,
      name: `${test.name} (Copy)`,
      last_result: "draft",
      last_executed: "Never",
    };
    setTests([duplicated, ...tests]);
    success("Test Duplicated", `Created draft test: "${duplicated.name}"`);
  };

  // Delete test
  const handleDeleteTest = (test: any) => {
    confirm({
      title: "Delete Test Case",
      message: `Are you sure you want to delete test case '${test.test_id} - ${test.name}'?`,
      confirmText: "Delete Test",
      variant: "danger",
      onConfirm: async () => {
        setTests(tests.filter((t) => t.id !== test.id));
        success("Test Deleted", `Test case "${test.test_id}" removed.`);
      },
    });
  };

  const filteredTests = tests.filter((t) => {
    const q = (searchQuery || "").trim().toLowerCase();
    const nameStr = (t?.name || "").toLowerCase();
    const idStr = (t?.test_id || "").toLowerCase();
    const descStr = (t?.description || "").toLowerCase();
    const matchesSearch = !q || nameStr.includes(q) || idStr.includes(q) || descStr.includes(q);
    const matchesStatus = statusFilter === "all" || t?.last_result === statusFilter;
    const matchesSuite = suiteFilter === "all" || t?.suite_name === suiteFilter;
    return matchesSearch && matchesStatus && matchesSuite;
  });

  const totalPages = Math.ceil(filteredTests.length / pageSize) || 1;
  const paginated = filteredTests.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-emerald-500" />
            <span>Test Cases</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Enterprise test case catalog supporting 12 deterministic assertion rules.
          </p>
        </div>

        <button
          onClick={() => onNavigate("testing_builder")}
          className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Test Case</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full md:w-80 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search test name, ID or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Result:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs focus:outline-none"
            >
              <option value="all">All Results</option>
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
              <option value="skipped">Skipped</option>
              <option value="blocked">Blocked</option>
              <option value="draft">Draft</option>
            </select>
          </div>
        </div>
      </div>

      {/* Test Cases Table */}
      <div className="bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 text-[10px] uppercase font-bold text-slate-400">
                <th className="py-3 px-4">Test Case & ID</th>
                <th className="py-3 px-3">Test Suite</th>
                <th className="py-3 px-3">Environment</th>
                <th className="py-3 px-3">Last Result</th>
                <th className="py-3 px-3">Last Executed</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <CheckSquare className="w-8 h-8 text-slate-400/40" />
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                        No test cases found in this workspace
                      </span>
                      <p className="text-[11px] text-slate-500 max-w-sm">
                        Create your first test case to assert DOM visibility, text content, and element state.
                      </p>
                      <button
                        type="button"
                        onClick={() => onNavigate("testing_builder")}
                        className="mt-2 px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-medium transition"
                      >
                        + Create First Test Case
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                paginated.map((test) => (
                <tr key={test.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                  <td className="py-3 px-4 max-w-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[#2563EB] dark:text-blue-400 font-bold">
                        {test.test_id}
                      </span>
                      <span className="font-semibold text-slate-900 dark:text-slate-100 text-xs">
                        {test.name}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">
                      {test.description}
                    </p>
                  </td>

                  <td className="py-3 px-3">
                    <span className="text-slate-700 dark:text-slate-300 font-medium">
                      {test.suite_name}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <span className="text-slate-600 dark:text-slate-400">
                      {test.environment}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                        test.last_result === "passed"
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : test.last_result === "failed"
                          ? "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800"
                          : test.last_result === "skipped"
                          ? "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                          : test.last_result === "blocked"
                          ? "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                          : "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800"
                      }`}
                    >
                      {test.last_result === "passed" && <CheckCircle2 className="w-3 h-3" />}
                      {test.last_result === "failed" && <XCircle className="w-3 h-3" />}
                      {test.last_result === "skipped" && <MinusCircle className="w-3 h-3" />}
                      {test.last_result === "blocked" && <AlertTriangle className="w-3 h-3" />}
                      <span>{test.last_result}</span>
                    </span>
                  </td>

                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400 text-[11px]">
                    {test.last_executed}
                  </td>

                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {/* Run Action */}
                      <button
                        onClick={() => handleRunTest(test)}
                        title="Execute Test Case"
                        className="p-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:hover:bg-emerald-900 text-emerald-700 dark:text-emerald-300 transition"
                      >
                        <Play className="w-3.5 h-3.5" />
                      </button>

                      {/* Edit Action */}
                      <button
                        onClick={() => {
                          if (onSelectTest) onSelectTest(test.id);
                          onNavigate("testing_builder");
                        }}
                        title="Edit in Test Builder"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      >
                        <Edit className="w-3.5 h-3.5" />
                      </button>

                      {/* Duplicate Action */}
                      <button
                        onClick={() => handleDuplicateTest(test)}
                        title="Duplicate Test"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>

                      {/* Delete Action */}
                      <button
                        onClick={() => handleDeleteTest(test)}
                        title="Delete Test Case"
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

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>Showing {paginated.length} of {filteredTests.length} test cases</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono px-2">Page {currentPage} of {totalPages}</span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
