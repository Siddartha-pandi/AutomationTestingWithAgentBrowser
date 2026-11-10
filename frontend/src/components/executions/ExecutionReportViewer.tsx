"use client";

import React, { useState, useEffect } from "react";
import {
  CheckCircle,
  XCircle,
  Clock,
  Terminal,
  Camera,
  Search,
  Filter,
  RefreshCw,
  Eye,
} from "lucide-react";
import { executionsApi } from "../../api";

interface ExecutionReportViewerProps {
  projectId?: string;
  initialExecutionId?: string;
  onSelectExecution?: (id: string) => void;
}

export const ExecutionReportViewer: React.FC<ExecutionReportViewerProps> = ({
  projectId,
  initialExecutionId,
  onSelectExecution,
}) => {
  const [executions, setExecutions] = useState<any[]>([]);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(
    initialExecutionId || null
  );
  const [selectedDetail, setSelectedDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"steps" | "logs" | "screenshots">("steps");
  const [zoomScreenshot, setZoomScreenshot] = useState<string | null>(null);

  useEffect(() => {
    if (initialExecutionId) {
      setSelectedExecutionId(initialExecutionId);
    }
  }, [initialExecutionId]);

  const loadExecutions = async () => {
    setLoading(true);
    try {
      const list = await executionsApi.list({ projectId });
      setExecutions(list);
      if (list.length > 0 && !selectedExecutionId) {
        setSelectedExecutionId(list[0].id);
      }
    } catch (err: any) {
      if (err?.message?.includes("Authentication") || err?.message?.includes("401")) {
        setExecutions([]);
      } else {
        console.warn("Could not load executions:", err?.message || err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExecutions();
  }, [projectId]);

  useEffect(() => {
    if (!selectedExecutionId) return;
    const fetchDetail = async () => {
      try {
        const detail = await executionsApi.get(selectedExecutionId);
        setSelectedDetail(detail);
      } catch (err: any) {
        if (!err?.message?.includes("Authentication") && !err?.message?.includes("401")) {
          console.warn("Could not load execution detail:", err?.message || err);
        }
      }
    };
    fetchDetail();
  }, [selectedExecutionId]);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", height: "calc(100vh - 120px)", background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "10px", overflow: "hidden" }}>
      {/* 1. Left List of Executions */}
      <div style={{ borderRight: "1px solid #e2e8f0", background: "#f8fafc", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "13px", fontWeight: 700, color: "#0f172a" }}>Executions ({executions.length})</span>
          <button onClick={loadExecutions} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer" }}>
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
          {executions.map((exec) => {
            const isSelected = exec.id === selectedExecutionId;
            return (
              <div
                key={exec.id}
                onClick={() => setSelectedExecutionId(exec.id)}
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid #e2e8f0",
                  cursor: "pointer",
                  background: isSelected ? "#eff6ff" : "transparent",
                  borderLeft: isSelected ? "3px solid #2563eb" : "3px solid transparent",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#0f172a" }}>
                    Run #{exec.id.substring(0, 8)}
                  </span>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 700,
                      padding: "2px 6px",
                      borderRadius: "4px",
                      background: exec.status === "passed" ? "#d1fae5" : exec.status === "failed" ? "#fee2e2" : "#f1f5f9",
                      color: exec.status === "passed" ? "#065f46" : exec.status === "failed" ? "#991b1b" : "#475569",
                      textTransform: "uppercase",
                    }}
                  >
                    {exec.status}
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {exec.duration_ms ? `${exec.duration_ms} ms` : "in progress"} &bull; {exec.trigger_type}
                </div>
              </div>
            );
          })}
          {executions.length === 0 && (
            <div style={{ padding: "30px 16px", textAlign: "center", color: "#94a3b8", fontSize: "12px" }}>
              No executions recorded yet.
            </div>
          )}
        </div>
      </div>

      {/* 2. Right Detail Panel */}
      {selectedDetail ? (
        <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#ffffff", overflow: "hidden" }}>
          {/* Header */}
          <div style={{ padding: "16px 20px", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "space-between", background: "#f8fafc" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: 700, color: "#0f172a", margin: 0 }}>
                  Execution Report {selectedDetail.id}
                </h3>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: selectedDetail.status === "passed" ? "#ecfdf5" : "#fef2f2",
                    color: selectedDetail.status === "passed" ? "#059669" : "#dc2626",
                  }}
                >
                  {selectedDetail.status.toUpperCase()}
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                Duration: {selectedDetail.duration_ms || 0} ms &bull; Steps: {selectedDetail.steps?.length || 0} &bull; Started: {selectedDetail.started_at || "N/A"}
              </div>
            </div>

            {/* Sub-tabs */}
            <div style={{ display: "flex", gap: "6px" }}>
              <button
                onClick={() => setActiveTab("steps")}
                style={{ padding: "6px 12px", borderRadius: "5px", border: "1px solid #cbd5e1", background: activeTab === "steps" ? "#2563eb" : "#ffffff", color: activeTab === "steps" ? "#ffffff" : "#475569", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
              >
                Steps ({selectedDetail.steps?.length || 0})
              </button>
              <button
                onClick={() => setActiveTab("logs")}
                style={{ padding: "6px 12px", borderRadius: "5px", border: "1px solid #cbd5e1", background: activeTab === "logs" ? "#2563eb" : "#ffffff", color: activeTab === "logs" ? "#ffffff" : "#475569", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
              >
                Logs ({selectedDetail.logs?.length || 0})
              </button>
              <button
                onClick={() => setActiveTab("screenshots")}
                style={{ padding: "6px 12px", borderRadius: "5px", border: "1px solid #cbd5e1", background: activeTab === "screenshots" ? "#2563eb" : "#ffffff", color: activeTab === "screenshots" ? "#ffffff" : "#475569", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
              >
                Screenshots
              </button>
            </div>
          </div>

          {/* Sub-tab Content */}
          <div style={{ flex: 1, padding: "20px", overflowY: "auto" }}>
            {activeTab === "steps" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {selectedDetail.steps?.map((step: any) => (
                  <div
                    key={step.id}
                    style={{
                      border: "1px solid #e2e8f0",
                      borderRadius: "6px",
                      padding: "12px 14px",
                      background: "#ffffff",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "#64748b" }}>#{step.step_index}</span>
                        <span style={{ fontSize: "12px", fontWeight: 700, color: "#0f172a" }}>{step.action}</span>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>[{step.step_type}]</span>
                      </div>
                      {step.error_message && (
                        <div style={{ fontSize: "11px", color: "#dc2626", marginTop: "4px" }}>
                          Error: {step.error_message}
                        </div>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <span style={{ fontSize: "11px", color: "#64748b" }}>{step.duration_ms} ms</span>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 700,
                          color: step.status === "passed" ? "#059669" : "#dc2626",
                        }}
                      >
                        {step.status.toUpperCase()}
                      </span>
                      {step.screenshot_path && (
                        <button
                          onClick={() => setZoomScreenshot(step.screenshot_path)}
                          style={{ background: "none", border: "none", color: "#2563eb", cursor: "pointer" }}
                        >
                          <Camera className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === "logs" && (
              <div style={{ background: "#0f172a", color: "#e2e8f0", borderRadius: "8px", padding: "16px", fontFamily: "var(--font-mono)", fontSize: "11px", lineHeight: "1.8", maxHeight: "500px", overflowY: "auto" }}>
                {selectedDetail.logs?.map((log: any) => (
                  <div key={log.id} style={{ display: "flex", gap: "10px" }}>
                    <span style={{ color: "#64748b" }}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span style={{ color: log.level === "ERROR" ? "#f87171" : "#38bdf8", fontWeight: 600 }}>[{log.level}]</span>
                    <span>{log.message}</span>
                  </div>
                ))}
                {(!selectedDetail.logs || selectedDetail.logs.length === 0) && (
                  <div style={{ color: "#64748b" }}>No log output recorded.</div>
                )}
              </div>
            )}

            {activeTab === "screenshots" && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "16px" }}>
                {selectedDetail.steps
                  ?.filter((s: any) => Boolean(s.screenshot_path))
                  .map((s: any) => (
                    <div key={s.id} style={{ border: "1px solid #e2e8f0", borderRadius: "6px", overflow: "hidden", background: "#f8fafc" }}>
                      <div style={{ height: "130px", background: "#cbd5e1", display: "grid", placeItems: "center", cursor: "pointer" }} onClick={() => setZoomScreenshot(s.screenshot_path)}>
                        <Camera className="w-8 h-8 text-slate-500" />
                      </div>
                      <div style={{ padding: "8px 10px", fontSize: "11px" }}>
                        <strong>Step #{s.step_index}</strong> ({s.action})
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div style={{ display: "grid", placeItems: "center", color: "#94a3b8", fontSize: "13px" }}>
          Select an execution run to inspect reports and logs.
        </div>
      )}

      {/* Screenshot Zoom Modal */}
      {zoomScreenshot && (
        <div
          onClick={() => setZoomScreenshot(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.75)",
            display: "grid",
            placeItems: "center",
            zIndex: 100,
          }}
        >
          <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", maxWidth: "90vw", maxHeight: "90vh" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "12px", fontWeight: 600 }}>Screenshot: {zoomScreenshot}</span>
              <button onClick={() => setZoomScreenshot(null)} style={{ border: "none", background: "none", cursor: "pointer", fontWeight: 700 }}>✕</button>
            </div>
            <div style={{ padding: "40px", background: "#f1f5f9", textAlign: "center", color: "#64748b", fontSize: "12px" }}>
              [Screenshot Verified Storage: {zoomScreenshot}]
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
