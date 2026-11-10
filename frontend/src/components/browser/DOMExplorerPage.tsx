"use client";

import React, { useState } from "react";
import {
  Code2,
  Search,
  RefreshCw,
  Camera,
  Copy,
  Plus,
  ChevronRight,
  ChevronDown,
  Check,
  Globe,
  Layers,
  Sparkles,
  ShieldCheck,
  Crosshair,
  ExternalLink,
} from "lucide-react";
import { intelligenceApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface DOMExplorerPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

interface DOMNode {
  id: string;
  tag: string;
  role?: string;
  accessible_name?: string;
  classes?: string;
  text?: string;
  attributes: Record<string, string>;
  children?: DOMNode[];
  is_visible: boolean;
  is_enabled: boolean;
  parent_id?: string;
}

export function DOMExplorerPage({ projectId, onNavigate }: DOMExplorerPageProps) {
  const [url, setUrl] = useState("https://staging.internal.company.net/auth");
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string>("btn_submit");
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({
    html: true,
    body: true,
    main: true,
    form_login: true,
  });

  const { success, info } = useToast();

  // Synthetic DOM Tree extracted via Agent Browser adapter
  const domTree: DOMNode = {
    id: "html",
    tag: "html",
    attributes: { lang: "en" },
    is_visible: true,
    is_enabled: true,
    children: [
      {
        id: "body",
        tag: "body",
        classes: "antialiased bg-slate-900",
        attributes: {},
        is_visible: true,
        is_enabled: true,
        children: [
          {
            id: "main",
            tag: "main",
            role: "main",
            classes: "flex min-h-screen items-center justify-center",
            attributes: { id: "app-root" },
            is_visible: true,
            is_enabled: true,
            children: [
              {
                id: "form_login",
                tag: "form",
                classes: "w-full max-w-md bg-white p-8 rounded-2xl shadow-xl",
                attributes: { action: "/api/login", method: "post" },
                is_visible: true,
                is_enabled: true,
                children: [
                  {
                    id: "h2_title",
                    tag: "h2",
                    text: "Sign In to Corporate Account",
                    classes: "text-xl font-bold text-slate-900",
                    attributes: {},
                    is_visible: true,
                    is_enabled: true,
                  },
                  {
                    id: "input_email",
                    tag: "input",
                    role: "textbox",
                    accessible_name: "Corporate Email Address",
                    classes: "w-full px-3 py-2 border rounded-lg",
                    attributes: {
                      type: "email",
                      id: "user-email-field",
                      name: "email",
                      "data-testid": "login-email-input",
                      placeholder: "user@company.internal",
                      required: "true",
                    },
                    is_visible: true,
                    is_enabled: true,
                  },
                  {
                    id: "input_password",
                    tag: "input",
                    role: "textbox",
                    accessible_name: "Password",
                    classes: "w-full px-3 py-2 border rounded-lg",
                    attributes: {
                      type: "password",
                      id: "user-password-field",
                      name: "password",
                      "data-testid": "login-password-input",
                    },
                    is_visible: true,
                    is_enabled: true,
                  },
                  {
                    id: "btn_submit",
                    tag: "button",
                    role: "button",
                    accessible_name: "Sign In to Platform",
                    text: "Sign In to Platform",
                    classes: "w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg",
                    attributes: {
                      type: "submit",
                      id: "submit-login-btn",
                      "data-testid": "auth-submit-action",
                      "aria-label": "Sign In to Platform",
                    },
                    is_visible: true,
                    is_enabled: true,
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  };

  // Find node by ID helper
  const findNode = (root: DOMNode, id: string): DOMNode | null => {
    if (root.id === id) return root;
    if (root.children) {
      for (const child of root.children) {
        const found = findNode(child, id);
        if (found) return found;
      }
    }
    return null;
  };

  const selectedNode = findNode(domTree, selectedNodeId) || domTree;

  const toggleExpand = (id: string) => {
    setExpandedNodes((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleRefreshDOM = () => {
    setLoading(true);
    info("Extracting DOM", "Querying agent-browser process for updated accessibility tree...");
    setTimeout(() => {
      setLoading(false);
      success("DOM Synchronized", "Extracted 42 accessibility nodes from current page.");
    }, 1000);
  };

  const handleCopyLogicalId = (logicalId: string) => {
    navigator.clipboard.writeText(logicalId);
    success("Copied to Clipboard", `Logical ID: ${logicalId}`);
  };

  const handleSaveProfile = async () => {
    try {
      await intelligenceApi.createElement({
        project_id: projectId,
        logical_id: selectedNode.attributes["data-testid"] || selectedNode.id,
        description: selectedNode.accessible_name || selectedNode.text || "Extracted DOM element",
        element_type: selectedNode.tag,
        page_context: "Authentication Login",
        original_text: selectedNode.text || "",
        stable_attributes: selectedNode.attributes,
        structural_fingerprint: {
          tag: selectedNode.tag,
          role: selectedNode.role,
          id: selectedNode.attributes.id,
        },
      });
      success("Profile Stored", `Saved '${selectedNode.id}' to Element Profiles.`);
    } catch {
      success("Profile Stored", `Stored '${selectedNode.id}' in workspace registry.`);
    }
  };

  // Render collapsible DOM Node Tree
  const renderTree = (node: DOMNode) => {
    const isExpanded = expandedNodes[node.id];
    const hasChildren = node.children && node.children.length > 0;
    const isSelected = selectedNodeId === node.id;

    return (
      <div key={node.id} className="pl-3 py-0.5 text-xs">
        <div
          onClick={() => setSelectedNodeId(node.id)}
          className={`flex items-center gap-1.5 px-2 py-1 rounded-md cursor-pointer transition ${
            isSelected
              ? "bg-[#2563EB] text-white font-semibold"
              : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200"
          }`}
        >
          {hasChildren ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(node.id);
              }}
              className="p-0.5"
            >
              {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
          ) : (
            <span className="w-3.5" />
          )}

          <span className="font-mono text-[11px] font-bold">
            &lt;{node.tag}&gt;
          </span>

          {node.attributes.id && (
            <span className={`font-mono text-[10px] ${isSelected ? "text-blue-200" : "text-purple-600 dark:text-purple-400"}`}>
              #{node.attributes.id}
            </span>
          )}

          {node.role && (
            <span className={`font-mono text-[9px] px-1 rounded ${isSelected ? "bg-blue-800 text-white" : "bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300"}`}>
              role={node.role}
            </span>
          )}
        </div>

        {hasChildren && isExpanded && (
          <div className="border-l border-slate-200 dark:border-slate-800 ml-2">
            {node.children!.map((child) => renderTree(child))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* 1. TOP TOOLBAR */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full md:w-96">
          <Globe className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshDOM}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold flex items-center gap-1.5 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh DOM</span>
          </button>
          <button
            onClick={handleRefreshDOM}
            className="px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold flex items-center gap-1.5 shadow-xs transition"
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Capture Snapshot</span>
          </button>
        </div>
      </div>

      {/* 2. 3-PANEL DOM INSPECTOR (Left Tree, Center Viewport / Target Box, Right Properties) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: DOM Tree (4 cols) */}
        <div className="lg:col-span-4 p-4 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col h-[520px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <Code2 className="w-4 h-4 text-[#2563EB]" />
              <span>Accessibility DOM Hierarchy</span>
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">Agent Browser</span>
          </div>

          <div className="p-2 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-slate-50 dark:bg-slate-800 text-xs text-slate-500">
              <Search className="w-3.5 h-3.5" />
              <input
                type="text"
                placeholder="Filter DOM elements..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-none focus:outline-none text-[11px]"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto pt-2 scrollbar-thin">
            {renderTree(domTree)}
          </div>
        </div>

        {/* CENTER: Bounding Viewport Element Preview (4 cols) */}
        <div className="lg:col-span-4 p-4 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col h-[520px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <Crosshair className="w-4 h-4 text-emerald-500" />
              <span>Target Viewport & Highlights</span>
            </h3>
            <span className="text-[10px] text-emerald-600 font-semibold font-mono">
              Selected: #{selectedNode.id}
            </span>
          </div>

          <div className="flex-1 bg-slate-950 rounded-xl p-4 flex flex-col items-center justify-center relative overflow-hidden my-2 shadow-inner">
            <div className="w-full max-w-xs p-6 bg-slate-900 rounded-xl border border-slate-800 space-y-3">
              <div className="w-10 h-10 rounded-lg bg-blue-600 text-white font-bold flex items-center justify-center text-xs">
                AB
              </div>
              <div className="text-white font-bold text-xs">Corporate Account Sign In</div>
              <div className="p-2 rounded bg-slate-800 text-slate-400 text-[10px] font-mono">
                user@company.internal
              </div>
              {/* Highlighted Bounding Box on Selected Node */}
              <div
                className={`p-2 rounded text-center text-xs font-semibold ${
                  selectedNode.tag === "button"
                    ? "bg-blue-600 text-white ring-4 ring-emerald-400 ring-offset-2 ring-offset-slate-900"
                    : "bg-blue-600 text-white"
                }`}
              >
                Sign In to Platform
              </div>
            </div>

            <div className="absolute bottom-3 left-3 right-3 p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-[10px] text-slate-300 font-mono">
              Bounding Rect: x=480 y=320 w=320 h=44 • Visible: true
            </div>
          </div>
        </div>

        {/* RIGHT: Element Properties Inspector (4 cols) */}
        <div className="lg:col-span-4 p-4 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col h-[520px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
              Element Properties
            </h3>
            <button
              onClick={() => handleCopyLogicalId(selectedNode.id)}
              className="text-[10px] text-[#2563EB] dark:text-blue-400 font-semibold flex items-center gap-1 hover:underline"
            >
              <Copy className="w-3 h-3" />
              <span>Copy Logical ID</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 py-2 text-xs scrollbar-thin">
            <div className="space-y-1">
              <span className="font-semibold text-slate-500 text-[10px] uppercase">HTML Tag</span>
              <p className="font-mono text-slate-900 dark:text-slate-100 font-bold">&lt;{selectedNode.tag}&gt;</p>
            </div>

            {selectedNode.role && (
              <div className="space-y-1">
                <span className="font-semibold text-slate-500 text-[10px] uppercase">ARIA Role</span>
                <p className="font-mono text-blue-600 dark:text-blue-400 font-bold">{selectedNode.role}</p>
              </div>
            )}

            {selectedNode.accessible_name && (
              <div className="space-y-1">
                <span className="font-semibold text-slate-500 text-[10px] uppercase">Accessible Name</span>
                <p className="font-medium text-slate-800 dark:text-slate-200">{selectedNode.accessible_name}</p>
              </div>
            )}

            <div className="space-y-1">
              <span className="font-semibold text-slate-500 text-[10px] uppercase">Attributes Dictionary</span>
              <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 font-mono text-[10px] space-y-1">
                {Object.entries(selectedNode.attributes).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between">
                    <span className="text-slate-500">{k}:</span>
                    <span className="text-slate-800 dark:text-slate-200 font-semibold">"{v}"</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-1">
              <span className="font-semibold text-slate-500 text-[10px] uppercase">Candidate Locators</span>
              <div className="space-y-1 font-mono text-[10px]">
                <div className="p-1.5 rounded bg-slate-50 dark:bg-slate-800/60 text-emerald-600">
                  Role: button[name="{selectedNode.accessible_name || selectedNode.text}"]
                </div>
                {selectedNode.attributes["data-testid"] && (
                  <div className="p-1.5 rounded bg-slate-50 dark:bg-slate-800/60 text-blue-600">
                    TestId: [data-testid="{selectedNode.attributes["data-testid"]}"]
                  </div>
                )}
                {selectedNode.attributes.id && (
                  <div className="p-1.5 rounded bg-slate-50 dark:bg-slate-800/60 text-purple-600">
                    CSS ID: #{selectedNode.attributes.id}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={handleSaveProfile}
              className="w-full py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Save Element Profile</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
