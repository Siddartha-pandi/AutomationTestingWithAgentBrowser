"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  Search,
  Filter,
  Check,
  ChevronRight,
  Crosshair,
  Lock,
  ArrowRight,
  HelpCircle,
  Layers,
} from "lucide-react";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";
import { intelligenceApi } from "@/api";

interface ElementRecognitionPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface CandidateMatch {
  rank: number;
  selector: string;
  tag: string;
  confidence_score: number;
  is_unique: boolean;
  is_visible: boolean;
  is_enabled: boolean;
  decision: "Accepted" | "Rejected";
  decision_reason: string;
  evidence: {
    matching_attributes: { attr: string; score: number }[];
    semantic_evidence: { criterion: string; match: string; score: number }[];
    structural_evidence: { criterion: string; score: number }[];
    context_evidence: { criterion: string; score: number }[];
  };
}

export function ElementRecognitionPage({ projectId, onNavigate }: ElementRecognitionPageProps) {
  const [elements, setElements] = useState<any[]>([]);
  const [selectedLogicalId, setSelectedLogicalId] = useState("");
  const [candidates, setCandidates] = useState<CandidateMatch[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadElements();
  }, [projectId]);

  const loadElements = async () => {
    setLoading(true);
    try {
      const list = await intelligenceApi.listElements(projectId);
      if (list && list.length > 0) {
        setElements(list);
        setSelectedLogicalId(list[0].logical_name || list[0].logical_id);
      } else {
        setElements([]);
        setSelectedLogicalId("");
      }
    } catch {
      setElements([]);
    } finally {
      setLoading(false);
    }
  };

  const activeElement = elements.find((el) => (el.logical_name || el.logical_id) === selectedLogicalId) || elements[0] || null;

  const originalProfile = activeElement ? {
    logical_id: activeElement.logical_name || activeElement.logical_id || "element_target",
    description: activeElement.description || "Profiled DOM element",
    page_context: activeElement.page_context || "Default Context",
    element_type: activeElement.element_type || "button",
    original_text: activeElement.text || "Element",
    expected_attributes: activeElement.stable_attributes || {},
    structural_path: "body > main",
  } : null;

  const selectedCandidate = candidates[0] || null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-600" />
            <span>Deterministic Element Recognition</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Transparent algorithmic scoring breakdown: Levenshtein distance, Jaccard ancestor sets, and ARIA semantics.
          </p>
        </div>

        {/* Safety Gate Indicator */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs font-semibold">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Action Safety Gate: Active (≥98% for mutations)</span>
        </div>
      </div>

      {/* Target Element Profile Summary Card */}
      {originalProfile && (
        <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Crosshair className="w-4 h-4 text-[#2563EB]" />
              <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                Active Element Profile: <strong className="font-mono text-[#2563EB]">{originalProfile.logical_id}</strong>
              </span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-[#2563EB] font-mono">
              {originalProfile.page_context}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs pt-2 border-t border-slate-100 dark:border-slate-800">
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Original Text</span>
              <span className="font-medium text-slate-800 dark:text-slate-200">{originalProfile.original_text}</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Element Tag</span>
              <span className="font-mono text-slate-800 dark:text-slate-200">&lt;{originalProfile.element_type}&gt;</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Target Attributes</span>
              <span className="font-mono text-[11px] text-slate-700 dark:text-slate-300">data-testid, role</span>
            </div>
          </div>
        </div>
      )}

      {/* Candidate Ranking & Scoring Evidence Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Candidate Ranking List (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
              Ranked DOM Candidates ({candidates.length})
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">Deterministic Sort</span>
          </div>

          <div className="space-y-3">
            {candidates.map((cand) => (
              <div
                key={cand.rank}
                className={`p-3.5 rounded-xl border transition ${
                  cand.decision === "Accepted"
                    ? "bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-800"
                    : "bg-slate-50/50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-mono text-[10px] font-bold flex items-center justify-center">
                      #{cand.rank}
                    </span>
                    <span className="font-mono text-[11px] font-bold text-slate-900 dark:text-slate-100">
                      &lt;{cand.tag}&gt;
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold font-mono text-emerald-600">
                      {cand.confidence_score}%
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                        cand.decision === "Accepted"
                          ? "bg-emerald-100 dark:bg-emerald-900 text-emerald-700 dark:text-emerald-300"
                          : "bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300"
                      }`}
                    >
                      {cand.decision}
                    </span>
                  </div>
                </div>

                <div className="mt-2 font-mono text-[10px] text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 p-1.5 rounded border border-slate-200 dark:border-slate-800 truncate">
                  {cand.selector}
                </div>

                <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 leading-snug">
                  <strong>Reason:</strong> {cand.decision_reason}
                </div>

                <div className="mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[10px] text-slate-400">
                  <span>Unique: <strong>{cand.is_unique ? "Yes" : "No"}</strong></span>
                  <span>Visible: <strong>{cand.is_visible ? "Yes" : "No"}</strong></span>
                  <span>Enabled: <strong>{cand.is_enabled ? "Yes" : "No"}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected Candidate Evidence Breakdown (7 cols) */}
        <div className="lg:col-span-7 p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
                Candidate Evidence Matrix (Rank #1)
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Mathematical multi-factor evidence components
              </p>
            </div>
            <span className="font-mono text-xs px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 font-bold">
              Confidence: {selectedCandidate.confidence_score}%
            </span>
          </div>

          <div className="space-y-4 text-xs">
            {/* Attribute Matching Evidence */}
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-2">
              <span className="font-bold text-slate-800 dark:text-slate-200 text-xs flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>Attribute Matching Evidence (Weight: 35%)</span>
              </span>
              <div className="space-y-1 text-[11px]">
                {selectedCandidate.evidence.matching_attributes.map((attr, idx) => (
                  <div key={idx} className="flex items-center justify-between font-mono">
                    <span className="text-slate-600 dark:text-slate-300">{attr.attr}</span>
                    <span className="text-emerald-600 font-bold">{attr.score}% match</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Semantic Evidence */}
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-2">
              <span className="font-bold text-slate-800 dark:text-slate-200 text-xs flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                <span>Semantic & Accessibility Evidence (Weight: 25%)</span>
              </span>
              <div className="space-y-1 text-[11px]">
                {selectedCandidate.evidence.semantic_evidence.map((sem, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-slate-600 dark:text-slate-300">{sem.criterion}: <em>{sem.match}</em></span>
                    <span className="font-mono text-emerald-600 font-bold">{sem.score}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Structural Evidence */}
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-2">
              <span className="font-bold text-slate-800 dark:text-slate-200 text-xs flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-purple-500" />
                <span>Structural & Ancestor Topology Evidence (Weight: 25%)</span>
              </span>
              <div className="space-y-1 text-[11px]">
                {selectedCandidate.evidence.structural_evidence.map((struct, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-slate-600 dark:text-slate-300">{struct.criterion}</span>
                    <span className="font-mono text-emerald-600 font-bold">{struct.score}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Context Evidence */}
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-2">
              <span className="font-bold text-slate-800 dark:text-slate-200 text-xs flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-amber-500" />
                <span>Context & Surrounding Environment Evidence (Weight: 15%)</span>
              </span>
              <div className="space-y-1 text-[11px]">
                {selectedCandidate.evidence.context_evidence.map((ctx, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-slate-600 dark:text-slate-300">{ctx.criterion}</span>
                    <span className="font-mono text-emerald-600 font-bold">{ctx.score}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
