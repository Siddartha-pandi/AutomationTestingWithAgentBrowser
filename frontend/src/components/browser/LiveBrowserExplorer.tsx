"use client";

import React, { useState, useEffect } from "react";
import {
  Globe,
  Search,
  Sparkles,
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertCircle,
  ExternalLink,
  Code,
  Layers,
  Fingerprint,
} from "lucide-react";
import { intelligenceApi } from "../../api";

interface LiveBrowserExplorerProps {
  projectId: string;
}

export const LiveBrowserExplorer: React.FC<LiveBrowserExplorerProps> = ({ projectId }) => {
  const [activeTab, setActiveTab] = useState<"dom" | "elements" | "healing" | "approvals">("elements");
  const [elements, setElements] = useState<any[]>([]);
  const [healingEvents, setHealingEvents] = useState<any[]>([]);
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [extractedDom, setExtractedDom] = useState<any | null>(null);

  // New Element Profile form state
  const [newLogicalId, setNewLogicalId] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newType, setNewType] = useState("button");
  const [newPageContext, setNewPageContext] = useState("Dashboard");
  const [newSelector, setNewSelector] = useState("");

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === "elements") {
        const elList = await intelligenceApi.listElements(projectId);
        setElements(elList);
      } else if (activeTab === "healing") {
        const healList = await intelligenceApi.listHealingEvents();
        setHealingEvents(healList);
      } else if (activeTab === "approvals") {
        const appList = await intelligenceApi.listApprovals("pending");
        setApprovals(appList);
      }
    } catch (err: any) {
      console.error("Error loading intelligence data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab, projectId]);

  const handleExtractDom = async () => {
    if (!sessionId.trim()) {
      alert("Please provide an active Agent Browser session ID");
      return;
    }
    setLoading(true);
    try {
      const res = await intelligenceApi.extractDom(sessionId);
      setExtractedDom(res);
    } catch (err: any) {
      alert(`DOM extraction failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLogicalId.trim() || !newSelector.trim()) {
      alert("Logical ID and Selector are required");
      return;
    }
    try {
      await intelligenceApi.createElement({
        project_id: projectId,
        logical_id: newLogicalId,
        description: newDesc,
        element_type: newType,
        page_context: newPageContext,
        stable_attributes: { selector: newSelector },
        structural_fingerprint: { selector: newSelector },
      });
      alert(`Created Element Profile '${newLogicalId}'!`);
      setNewLogicalId("");
      setNewSelector("");
      loadData();
    } catch (err: any) {
      alert(`Failed to create element profile: ${err.message}`);
    }
  };

  const handleRespondApproval = async (id: string, decision: "approved" | "rejected") => {
    const comment = prompt(`Enter comments for ${decision} action:`, `Operator ${decision}`);
    try {
      await intelligenceApi.respondApproval(id, decision, comment || undefined);
      alert(`Approval ${decision} successfully!`);
      loadData();
    } catch (err: any) {
      alert(`Approval response failed: ${err.message}`);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 120px)", background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "10px", overflow: "hidden" }}>
      {/* 1. Sub-nav tabs */}
      <div style={{ display: "flex", alignItems: "center", gap: "24px", padding: "0 20px", borderBottom: "1px solid #e2e8f0", background: "#f8fafc" }}>
        <button
          onClick={() => setActiveTab("elements")}
          style={{ padding: "14px 0", border: "none", borderBottom: activeTab === "elements" ? "2px solid #2563eb" : "none", color: activeTab === "elements" ? "#2563eb" : "#64748b", fontWeight: 600, fontSize: "13px", cursor: "pointer", background: "transparent" }}
        >
          Element Profiles ({elements.length})
        </button>
        <button
          onClick={() => setActiveTab("dom")}
          style={{ padding: "14px 0", border: "none", borderBottom: activeTab === "dom" ? "2px solid #2563eb" : "none", color: activeTab === "dom" ? "#2563eb" : "#64748b", fontWeight: 600, fontSize: "13px", cursor: "pointer", background: "transparent" }}
        >
          DOM Explorer
        </button>
        <button
          onClick={() => setActiveTab("healing")}
          style={{ padding: "14px 0", border: "none", borderBottom: activeTab === "healing" ? "2px solid #2563eb" : "none", color: activeTab === "healing" ? "#2563eb" : "#64748b", fontWeight: 600, fontSize: "13px", cursor: "pointer", background: "transparent" }}
        >
          Self-Healing History ({healingEvents.length})
        </button>
        <button
          onClick={() => setActiveTab("approvals")}
          style={{ padding: "14px 0", border: "none", borderBottom: activeTab === "approvals" ? "2px solid #2563eb" : "none", color: activeTab === "approvals" ? "#2563eb" : "#64748b", fontWeight: 600, fontSize: "13px", cursor: "pointer", background: "transparent" }}
        >
          Pending Operator Approvals ({approvals.length})
        </button>
      </div>

      {/* 2. Content */}
      <div style={{ flex: 1, padding: "20px", overflowY: "auto", background: "#f8fafc" }}>
        {activeTab === "elements" && (
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "20px" }}>
            {/* Element Profile List */}
            <div>
              <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", marginBottom: "12px" }}>Registered Element Profiles</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {elements.map((el) => (
                  <div key={el.id} style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px", display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "#1e40af" }}>{el.logical_id}</span>
                      <span style={{ fontSize: "11px", fontWeight: 600, padding: "2px 8px", background: "#f1f5f9", borderRadius: "4px", color: "#475569" }}>{el.element_type}</span>
                    </div>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>{el.description || "No description"}</p>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>Page Context: {el.page_context}</div>
                    {el.history?.length > 0 && (
                      <div style={{ marginTop: "6px", fontSize: "11px", color: "#059669", background: "#ecfdf5", padding: "4px 8px", borderRadius: "4px" }}>
                        Verified Selector: {el.history[0].locator_value} ({el.history[0].success_count} verified hits)
                      </div>
                    )}
                  </div>
                ))}
                {elements.length === 0 && (
                  <div style={{ textAlign: "center", padding: "40px", color: "#94a3b8", fontSize: "13px" }}>No element profiles registered yet.</div>
                )}
              </div>
            </div>

            {/* Create Profile Form */}
            <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "18px", height: "fit-content" }}>
              <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", marginBottom: "12px" }}>Create Deterministic Profile</h3>
              <form onSubmit={handleCreateProfile} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 600, color: "#475569" }}>Logical ID</label>
                  <input value={newLogicalId} onChange={(e) => setNewLogicalId(e.target.value)} placeholder="e.g. referral_submit" style={{ width: "100%", padding: "7px 10px", border: "1px solid #cbd5e1", borderRadius: "5px", fontSize: "12px" }} />
                </div>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 600, color: "#475569" }}>Element Type</label>
                  <select value={newType} onChange={(e) => setNewType(e.target.value)} style={{ width: "100%", padding: "7px 10px", border: "1px solid #cbd5e1", borderRadius: "5px", fontSize: "12px", background: "#ffffff" }}>
                    <option value="button">Button</option>
                    <option value="input">Input Field</option>
                    <option value="select">Select Dropdown</option>
                    <option value="link">Anchor Link</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 600, color: "#475569" }}>Page Context</label>
                  <input value={newPageContext} onChange={(e) => setNewPageContext(e.target.value)} placeholder="e.g. Referral Dashboard" style={{ width: "100%", padding: "7px 10px", border: "1px solid #cbd5e1", borderRadius: "5px", fontSize: "12px" }} />
                </div>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 600, color: "#475569" }}>Stable Selector / Test ID</label>
                  <input value={newSelector} onChange={(e) => setNewSelector(e.target.value)} placeholder="e.g. button#submit-referral" style={{ width: "100%", padding: "7px 10px", border: "1px solid #cbd5e1", borderRadius: "5px", fontSize: "12px" }} />
                </div>
                <div>
                  <label style={{ fontSize: "11px", fontWeight: 600, color: "#475569" }}>Description</label>
                  <input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Action performed by this element" style={{ width: "100%", padding: "7px 10px", border: "1px solid #cbd5e1", borderRadius: "5px", fontSize: "12px" }} />
                </div>
                <button type="submit" style={{ marginTop: "6px", padding: "9px 14px", background: "#2563eb", color: "#ffffff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                  Register Profile
                </button>
              </form>
            </div>
          </div>
        )}

        {activeTab === "dom" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", gap: "10px", background: "#ffffff", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <input
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                placeholder="Active Agent Browser Session ID (UUID)"
                style={{ flex: 1, padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "13px" }}
              />
              <button onClick={handleExtractDom} style={{ padding: "8px 18px", background: "#2563eb", color: "#ffffff", border: "none", borderRadius: "6px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                Extract DOM
              </button>
            </div>

            {extractedDom && (
              <div style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "16px" }}>
                <h4 style={{ fontSize: "13px", fontWeight: 700, marginBottom: "8px" }}>Page: {extractedDom.page_title} ({extractedDom.page_url})</h4>
                <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "12px" }}>Total Interactive Elements: {extractedDom.total_elements}</div>
                <div style={{ maxHeight: "400px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px" }}>
                  {extractedDom.elements?.map((node: any, idx: number) => (
                    <div key={idx} style={{ padding: "8px 12px", background: "#f8fafc", borderRadius: "6px", fontSize: "11px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div>
                        <strong style={{ color: "#1e40af" }}>&lt;{node.tag}&gt;</strong> role={node.role || "none"} name=&quot;{node.accessible_name || node.text || ""}&quot;
                      </div>
                      <span style={{ color: "#64748b" }}>{node.element_id ? `#${node.element_id}` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "healing" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a" }}>Deterministic Self-Healing Audit History</h3>
            {healingEvents.map((evt) => (
              <div key={evt.id} style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "14px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>
                    Original: <code style={{ color: "#dc2626" }}>{evt.original_locator}</code> &rarr; Healed: <code style={{ color: "#059669" }}>{evt.healed_locator}</code>
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                    Decision: <strong>{evt.decision}</strong> | Approved: {evt.is_approved ? "Yes" : "No"} | Timestamp: {evt.timestamp}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: evt.confidence_score >= 0.95 ? "#059669" : "#d97706" }}>
                    {(evt.confidence_score * 100).toFixed(1)}%
                  </span>
                  <div style={{ fontSize: "10px", color: "#94a3b8" }}>Confidence Score</div>
                </div>
              </div>
            ))}
            {healingEvents.length === 0 && <div style={{ textAlign: "center", padding: "40px", color: "#94a3b8", fontSize: "13px" }}>No self-healing events recorded yet.</div>}
          </div>
        )}

        {activeTab === "approvals" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a" }}>Pending Human Operator Confirmation (85-94% Confidence Tier)</h3>
            {approvals.map((appr) => (
              <div key={appr.id} style={{ background: "#ffffff", border: "1px solid #fde68a", borderRadius: "8px", padding: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: "#92400e" }}>Awaiting Confirmation</div>
                  <div style={{ fontSize: "12px", color: "#475569", marginTop: "4px" }}>{appr.comment}</div>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>Created: {appr.created_at}</div>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button onClick={() => handleRespondApproval(appr.id, "approved")} style={{ padding: "6px 14px", background: "#10b981", color: "#ffffff", border: "none", borderRadius: "5px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                    Approve
                  </button>
                  <button onClick={() => handleRespondApproval(appr.id, "rejected")} style={{ padding: "6px 14px", background: "#ef4444", color: "#ffffff", border: "none", borderRadius: "5px", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
                    Reject
                  </button>
                </div>
              </div>
            ))}
            {approvals.length === 0 && <div style={{ textAlign: "center", padding: "40px", color: "#94a3b8", fontSize: "13px" }}>No pending approvals. All recoveries are verified!</div>}
          </div>
        )}
      </div>
    </div>
  );
};

