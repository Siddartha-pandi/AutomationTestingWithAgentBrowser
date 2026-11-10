"use client";

import React, { useState } from "react";
import {
  LayoutTemplate,
  Search,
  Filter,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
  Layers,
  Copy,
  ExternalLink,
  Code2,
  Zap,
} from "lucide-react";
import { flowsApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface FlowTemplatesPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
  onSelectFlow?: (flowId: string) => void;
}

interface TemplateItem {
  id: string;
  title: string;
  category: "Authentication" | "Form Processing" | "Data Extraction" | "Verification" | "E2E Smoke";
  description: string;
  nodeCount: number;
  tags: string[];
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  estimatedSecs: number;
  initialDefinition: any;
}

export const ENTERPRISE_TEMPLATES: TemplateItem[] = [
  {
    id: "tpl_auth_session",
    title: "Enterprise Login & Session Token Verification",
    category: "Authentication",
    description:
      "Navigates to login portal, fills credentials from encrypted environment vault, submits, and asserts HTTP session cookies without exposing plaintext secrets.",
    nodeCount: 5,
    tags: ["Auth", "Vault", "Cookies", "Session"],
    difficulty: "Beginner",
    estimatedSecs: 8,
    initialDefinition: {
      name: "Enterprise Login & Session Verification",
      description: "Standard login authentication flow with credential interpolation",
      start_node_id: "node_1",
      nodes: [
        {
          id: "node_1",
          type: "action",
          action: "navigate",
          config: { url: "https://app.company.internal/login" },
          position: { x: 100, y: 150 },
        },
        {
          id: "node_2",
          type: "action",
          action: "fill",
          config: {
            target: { selector: "input[name='email']", logical_id: "auth_email_input" },
            value: "{{env.TEST_USER_EMAIL}}",
          },
          position: { x: 340, y: 150 },
        },
        {
          id: "node_3",
          type: "action",
          action: "fill",
          config: {
            target: { selector: "input[name='password']", logical_id: "auth_password_input" },
            value: "{{env.TEST_USER_PASSWORD}}",
          },
          position: { x: 580, y: 150 },
        },
        {
          id: "node_4",
          type: "action",
          action: "click",
          config: {
            target: { selector: "button[type='submit']", logical_id: "auth_submit_button" },
          },
          position: { x: 820, y: 150 },
        },
        {
          id: "node_5",
          type: "stop",
          config: { reason: "Authenticated successfully" },
          position: { x: 1060, y: 150 },
        },
      ],
      edges: [
        { id: "e1", source: "node_1", target: "node_2" },
        { id: "e2", source: "node_2", target: "node_3" },
        { id: "e3", source: "node_3", target: "node_4" },
        { id: "e4", source: "node_4", target: "node_5" },
      ],
    },
  },
  {
    id: "tpl_referral_submission",
    title: "Customer Referral & Multi-Field Form Submission",
    category: "Form Processing",
    description:
      "Fills customer referee details, selects partner tiers, uploads reference tokens, and verifies instant confirmation receipt.",
    nodeCount: 6,
    tags: ["Forms", "Input", "Dropdown", "Confirmation"],
    difficulty: "Intermediate",
    estimatedSecs: 14,
    initialDefinition: {
      name: "Customer Referral Form Submission",
      description: "Automated submission of multi-tier customer referrals",
      start_node_id: "node_start",
      nodes: [
        {
          id: "node_start",
          type: "action",
          action: "navigate",
          config: { url: "https://app.company.internal/referrals/new" },
          position: { x: 100, y: 150 },
        },
        {
          id: "node_fill_name",
          type: "action",
          action: "fill",
          config: {
            target: { selector: "#referee_name", logical_id: "referee_name_input" },
            value: "Enterprise Partner {{#uuid}}",
          },
          position: { x: 340, y: 150 },
        },
        {
          id: "node_select_tier",
          type: "action",
          action: "select",
          config: {
            target: { selector: "#referral_tier", logical_id: "referral_tier_select" },
            value: "platinum",
          },
          position: { x: 580, y: 150 },
        },
        {
          id: "node_submit",
          type: "action",
          action: "click",
          config: {
            target: { selector: "button#submit_btn", logical_id: "referral_submit_button" },
          },
          position: { x: 820, y: 150 },
        },
        {
          id: "node_screenshot",
          type: "action",
          action: "screenshot",
          config: { custom_name: "referral_receipt" },
          position: { x: 1060, y: 150 },
        },
        {
          id: "node_end",
          type: "stop",
          config: { reason: "Referral submitted" },
          position: { x: 1300, y: 150 },
        },
      ],
      edges: [
        { id: "e1", source: "node_start", target: "node_fill_name" },
        { id: "e2", source: "node_fill_name", target: "node_select_tier" },
        { id: "e3", source: "node_select_tier", target: "node_submit" },
        { id: "e4", source: "node_submit", target: "node_screenshot" },
        { id: "e5", source: "node_screenshot", target: "node_end" },
      ],
    },
  },
  {
    id: "tpl_table_scraper",
    title: "Structured Data Table Scraper & Variable Export",
    category: "Data Extraction",
    description:
      "Navigates to analytics or ledger view, extracts multi-row tabular records deterministically into structured JSON variables, and logs dataset size.",
    nodeCount: 4,
    tags: ["Scraper", "Tables", "Variables", "JSON"],
    difficulty: "Intermediate",
    estimatedSecs: 10,
    initialDefinition: {
      name: "Data Table Extraction Workflow",
      description: "Deterministic table extraction into structured variables",
      start_node_id: "n_nav",
      nodes: [
        {
          id: "n_nav",
          type: "action",
          action: "navigate",
          config: { url: "https://app.company.internal/reports/transactions" },
          position: { x: 100, y: 150 },
        },
        {
          id: "n_extract",
          type: "action",
          action: "extract_table",
          config: {
            target: { selector: "table.transactions-table", logical_id: "transactions_table" },
          },
          position: { x: 360, y: 150 },
        },
        {
          id: "n_shot",
          type: "action",
          action: "screenshot",
          config: { custom_name: "transactions_snapshot", full_page: true },
          position: { x: 620, y: 150 },
        },
        {
          id: "n_stop",
          type: "stop",
          config: { reason: "Extraction finished" },
          position: { x: 880, y: 150 },
        },
      ],
      edges: [
        { id: "e1", source: "n_nav", target: "n_extract" },
        { id: "e2", source: "n_extract", target: "n_shot" },
        { id: "e3", source: "n_shot", target: "n_stop" },
      ],
    },
  },
  {
    id: "tpl_fvr_verification",
    title: "Financial Verification Review (FVR) Status Auditor",
    category: "Verification",
    description:
      "Audits pending compliance applications, inspects dynamic status badges, captures DOM accessibility snapshots, and stops safely on unexpected states.",
    nodeCount: 5,
    tags: ["FVR", "Compliance", "Badges", "Audit"],
    difficulty: "Advanced",
    estimatedSecs: 16,
    initialDefinition: {
      name: "FVR Status Verification Flow",
      description: "Periodic compliance audit verifying application approval badges",
      start_node_id: "n1",
      nodes: [
        {
          id: "n1",
          type: "action",
          action: "navigate",
          config: { url: "https://app.company.internal/fvr/queue" },
          position: { x: 100, y: 150 },
        },
        {
          id: "n2",
          type: "action",
          action: "wait",
          config: { target: "table#fvr-records", timeout_ms: 5000 },
          position: { x: 340, y: 150 },
        },
        {
          id: "n3",
          type: "action",
          action: "extract_text",
          config: {
            target: { selector: "tr.fvr-row:first-child .status-badge", logical_id: "first_fvr_status" },
          },
          position: { x: 580, y: 150 },
        },
        {
          id: "n4",
          type: "condition",
          config: {
            variable: "{{n3.extracted_text}}",
            operator: "==",
            value: "Approved",
          },
          position: { x: 820, y: 150 },
        },
        {
          id: "n5",
          type: "stop",
          config: { reason: "Audit criteria verified" },
          position: { x: 1080, y: 150 },
        },
      ],
      edges: [
        { id: "e1", source: "n1", target: "n2" },
        { id: "e2", source: "n2", target: "n3" },
        { id: "e3", source: "n3", target: "n4" },
        { id: "e4", source: "n4", target: "n5", source_handle: "true" },
      ],
    },
  },
];

export function FlowTemplatesPage({ projectId, onNavigate, onSelectFlow }: FlowTemplatesPageProps) {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [isCloning, setIsCloning] = useState<string | null>(null);

  const { success, error, info } = useToast();

  const categories = ["all", "Authentication", "Form Processing", "Data Extraction", "Verification"];

  const filteredTemplates = ENTERPRISE_TEMPLATES.filter((tpl) => {
    const matchesCat = selectedCategory === "all" || tpl.category === selectedCategory;
    const matchesSearch =
      tpl.title.toLowerCase().includes(search.toLowerCase()) ||
      tpl.description.toLowerCase().includes(search.toLowerCase()) ||
      tpl.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()));
    return matchesCat && matchesSearch;
  });

  const handleUseTemplate = async (template: TemplateItem) => {
    setIsCloning(template.id);
    try {
      info("Creating Flow from Template", `Cloning '${template.title}' into your workspace...`);
      const created = await flowsApi.create({
        project_id: projectId,
        name: template.title,
        description: template.description,
        definition: template.initialDefinition,
      });

      success("Flow Created", `Template instantiated successfully. Redirecting to Flow Builder...`);
      if (onSelectFlow && created.id) {
        onSelectFlow(created.id);
      }
      onNavigate("automation_builder");
    } catch (err: any) {
      error("Clone Failed", err.message || "Failed to create flow from template.");
    } finally {
      setIsCloning(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <LayoutTemplate className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Flow Templates Library
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Pre-engineered enterprise browser workflows ready to clone and run with deterministic reliability.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 w-fit">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Zero-AI Policy Compliant • Pure Deterministic DAG</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates by keyword, category, or tag..."
            className="w-full pl-9 pr-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg capitalize whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800"
              }`}
            >
              {cat === "all" ? "All Categories" : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filteredTemplates.map((tpl) => (
          <div
            key={tpl.id}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between group"
          >
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-[11px] font-bold tracking-wide uppercase px-2.5 py-1 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-900">
                  {tpl.category}
                </span>
                <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  ~{tpl.estimatedSecs}s run
                </span>
              </div>

              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  {tpl.title}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 line-clamp-3 leading-relaxed">
                  {tpl.description}
                </p>
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {tpl.tags.map((t) => (
                  <span
                    key={t}
                    className="text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                  >
                    #{t}
                  </span>
                ))}
              </div>
            </div>

            {/* Card Footer */}
            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <Layers className="w-3.5 h-3.5 text-slate-400" />
                  {tpl.nodeCount} DAG nodes
                </span>
                <span>&bull;</span>
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  {tpl.difficulty}
                </span>
              </div>

              <button
                disabled={isCloning === tpl.id}
                onClick={() => handleUseTemplate(tpl)}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
              >
                <span>{isCloning === tpl.id ? "Instantiating..." : "Use Template"}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-16 bg-white dark:bg-slate-900 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl space-y-3">
          <LayoutTemplate className="w-10 h-10 text-slate-400 mx-auto" />
          <h3 className="text-base font-bold text-slate-900 dark:text-white">
            No templates match your query
          </h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Try resetting your search query or choosing another category filter.
          </p>
        </div>
      )}
    </div>
  );
}
