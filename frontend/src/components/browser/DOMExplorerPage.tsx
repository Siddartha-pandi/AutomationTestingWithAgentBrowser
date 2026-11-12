"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Code2,
  Search,
  RefreshCw,
  Camera,
  Copy,
  Plus,
  ChevronRight,
  ChevronDown,
  Globe,
  Layers,
  Sparkles,
  ShieldCheck,
  Crosshair,
  ExternalLink,
  Eye,
  CheckCircle2,
  AlertCircle,
  Loader2,
  MousePointerClick,
} from "lucide-react";
import { intelligenceApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface DOMExplorerPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

export interface ExtractedElement {
  tag: string;
  role?: string | null;
  accessible_name?: string | null;
  text?: string;
  element_id?: string | null;
  stable_attributes: Record<string, string>;
  aria_properties: Record<string, string>;
  associated_label?: string | null;
  ancestors: Array<{ tag: string; id?: string | null; role?: string | null; test_id?: string | null; depth: number }>;
  siblings?: { prev_tag?: string | null; next_tag?: string | null };
  nearby_heading?: string | null;
  is_visible: boolean;
  is_enabled: boolean;
  box: { x?: number; y?: number; width?: number; height?: number };
  page_url?: string;
}

export function DOMExplorerPage({ projectId, onNavigate }: DOMExplorerPageProps) {
  const [url, setUrl] = useState("https://mahila-action-vsk.vercel.app/");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [pageTitle, setPageTitle] = useState("");
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [elements, setElements] = useState<ExtractedElement[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<"all" | "interactive" | "visible">("interactive");
  const [imgScale, setImgScale] = useState<{ scaleX: number; scaleY: number }>({ scaleX: 1, scaleY: 1 });

  const imgRef = useRef<HTMLImageElement>(null);
  const { success, error, info } = useToast();

  const handleExploreDOM = async (targetUrl?: string) => {
    const rawUrl = (targetUrl || url).trim();
    if (!rawUrl) {
      error("URL Required", "Please enter a valid target URL to explore.");
      return;
    }

    let normalizedUrl = rawUrl;
    if (!normalizedUrl.startsWith("http://") && !normalizedUrl.startsWith("https://")) {
      normalizedUrl = `https://${normalizedUrl}`;
      setUrl(normalizedUrl);
    }

    setLoading(true);
    info("Exploring DOM", `Connecting Agent Browser session to ${normalizedUrl}...`);

    try {
      const res = await intelligenceApi.exploreDom(
        projectId || "p1-default",
        normalizedUrl,
        sessionId || undefined
      );

      if (res) {
        if (res.session_id) setSessionId(res.session_id);
        if (res.page_title) setPageTitle(res.page_title);
        if (res.screenshot) setScreenshotUrl(res.screenshot);
        if (res.elements && Array.isArray(res.elements) && res.elements.length > 0) {
          setElements(res.elements);
          // Pick the first interactive/meaningful element
          const firstInteractive = res.elements.findIndex(
            (el: ExtractedElement) =>
              ["button", "input", "a", "select", "textarea"].includes(el.tag) ||
              Boolean(el.role) ||
              Boolean(el.accessible_name) ||
              Boolean(el.stable_attributes?.["data-testid"])
          );
          setSelectedIdx(firstInteractive >= 0 ? firstInteractive : 0);
        }
        success(
          "DOM Synchronized",
          `Extracted ${res.total_elements || res.elements?.length || 0} elements from '${res.page_title || normalizedUrl}'.`
        );
      }
    } catch (err: any) {
      error("Exploration Failed", err.message || "Failed to explore DOM with Agent Browser.");
    } finally {
      setLoading(false);
    }
  };

  // Auto explore on mount
  useEffect(() => {
    if (elements.length === 0 && !loading && url) {
      handleExploreDOM(url);
    }
  }, []);

  const updateImageScale = () => {
    if (imgRef.current && imgRef.current.naturalWidth > 0) {
      setImgScale({
        scaleX: imgRef.current.clientWidth / imgRef.current.naturalWidth,
        scaleY: imgRef.current.clientHeight / imgRef.current.naturalHeight,
      });
    }
  };

  const selectedElement: ExtractedElement | null =
    elements.length > 0 && selectedIdx >= 0 && selectedIdx < elements.length
      ? elements[selectedIdx]
      : null;

  // Filter elements by user search query and type filter
  const filteredElements = elements.filter((el) => {
    if (filterType === "visible" && !el.is_visible) return false;
    if (filterType === "interactive") {
      const isInteractive =
        ["button", "input", "a", "select", "textarea", "form", "h1", "h2", "h3", "header", "nav", "main", "footer"].includes(el.tag) ||
        Boolean(el.role) ||
        Boolean(el.accessible_name) ||
        Boolean(el.stable_attributes?.["data-testid"]) ||
        Boolean(el.stable_attributes?.id);
      if (!isInteractive) return false;
    }

    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const tagMatch = el.tag.toLowerCase().includes(q);
    const idMatch = (el.element_id || el.stable_attributes?.id || "").toLowerCase().includes(q);
    const testIdMatch = (el.stable_attributes?.["data-testid"] || "").toLowerCase().includes(q);
    const textMatch = (el.text || "").toLowerCase().includes(q);
    const nameMatch = (el.accessible_name || "").toLowerCase().includes(q);
    const roleMatch = (el.role || "").toLowerCase().includes(q);

    return tagMatch || idMatch || testIdMatch || textMatch || nameMatch || roleMatch;
  });

  // Clicking directly on the viewport image selects the closest element under click coordinates
  const handleViewportClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) / imgScale.scaleX;
    const clickY = (e.clientY - rect.top) / imgScale.scaleY;

    let bestIdx = -1;
    let minArea = Infinity;

    elements.forEach((el, idx) => {
      if (el.box && typeof el.box.x === "number" && typeof el.box.width === "number") {
        const bx = el.box.x;
        const by = el.box.y || 0;
        const bw = el.box.width;
        const bh = el.box.height || 0;

        if (clickX >= bx && clickX <= bx + bw && clickY >= by && clickY <= by + bh) {
          const area = bw * bh;
          if (area > 0 && area < minArea) {
            minArea = area;
            bestIdx = idx;
          }
        }
      }
    });

    if (bestIdx >= 0) {
      setSelectedIdx(bestIdx);
    }
  };

  // Candidate locators computation
  const getCandidateLocators = (el: ExtractedElement | null) => {
    if (!el) return [];
    const locators: Array<{ label: string; value: string; color: string }> = [];

    const testId = el.stable_attributes?.["data-testid"] || el.stable_attributes?.["data-test"];
    if (testId) {
      locators.push({
        label: "Data TestID",
        value: `[data-testid="${testId}"]`,
        color: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60",
      });
    }

    const id = el.element_id || el.stable_attributes?.id;
    if (id) {
      locators.push({
        label: "CSS ID",
        value: `#${id}`,
        color: "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/60",
      });
    }

    if (el.role && el.accessible_name) {
      locators.push({
        label: "ARIA Role + Name",
        value: `${el.role}[name="${el.accessible_name}"]`,
        color: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60",
      });
    } else if (el.accessible_name) {
      locators.push({
        label: "Accessible Name",
        value: `${el.tag}[aria-label="${el.accessible_name}"]`,
        color: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60",
      });
    }

    const name = el.stable_attributes?.name;
    if (name) {
      locators.push({
        label: "Name Attribute",
        value: `${el.tag}[name="${name}"]`,
        color: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60",
      });
    }

    const placeholder = el.stable_attributes?.placeholder;
    if (placeholder) {
      locators.push({
        label: "Placeholder",
        value: `${el.tag}[placeholder="${placeholder}"]`,
        color: "text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/60",
      });
    }

    const href = el.stable_attributes?.href;
    if (href && el.tag === "a") {
      locators.push({
        label: "Link Target",
        value: `a[href="${href}"]`,
        color: "text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/60",
      });
    }

    if (el.text && el.text.trim().length > 0 && el.text.trim().length <= 40) {
      locators.push({
        label: "Text Locator",
        value: `${el.tag}:has-text("${el.text.trim()}")`,
        color: "text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/60",
      });
    }

    // Default tag fallback
    if (locators.length === 0) {
      locators.push({
        label: "Tag Selector",
        value: el.tag,
        color: "text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800",
      });
    }

    return locators;
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    success("Copied to Clipboard", `${label}: ${text}`);
  };

  const handleSaveProfile = async () => {
    if (!selectedElement) return;

    const locators = getCandidateLocators(selectedElement);
    const primarySelector = locators[0]?.value || selectedElement.tag;
    const logicalId =
      selectedElement.stable_attributes?.["data-testid"] ||
      selectedElement.element_id ||
      (selectedElement.accessible_name ? selectedElement.accessible_name.toLowerCase().replace(/[^a-z0-9]+/g, "_") : null) ||
      `${selectedElement.tag}_${Date.now().toString(36).slice(-4)}`;

    try {
      await intelligenceApi.createElement({
        project_id: projectId || "p1-default",
        logical_id: logicalId,
        description: selectedElement.accessible_name || selectedElement.text || `Extracted ${selectedElement.tag} element`,
        element_type: selectedElement.tag,
        page_context: pageTitle || url || "Default Page",
        original_text: selectedElement.text || selectedElement.accessible_name || "",
        stable_attributes: {
          ...selectedElement.stable_attributes,
          ...selectedElement.aria_properties,
          selector: primarySelector,
        },
        structural_fingerprint: {
          tag: selectedElement.tag,
          role: selectedElement.role,
          ancestors: selectedElement.ancestors,
          box: selectedElement.box,
        },
      });
      success("Profile Stored", `Saved '${logicalId}' to Element Profiles.`);
    } catch (err: any) {
      error("Storage Error", err.message || "Failed to store element profile.");
    }
  };

  const candidateLocators = getCandidateLocators(selectedElement);

  // Scaled bounding box coordinates for overlay
  const boxX = selectedElement?.box?.x !== undefined ? (selectedElement.box.x || 0) * imgScale.scaleX : null;
  const boxY = selectedElement?.box?.y !== undefined ? (selectedElement.box.y || 0) * imgScale.scaleY : null;
  const boxW = selectedElement?.box?.width !== undefined ? Math.max(6, (selectedElement.box.width || 0) * imgScale.scaleX) : null;
  const boxH = selectedElement?.box?.height !== undefined ? Math.max(6, (selectedElement.box.height || 0) * imgScale.scaleY) : null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* 1. TOP TOOLBAR */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 w-full md:w-2/3">
          <Globe className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleExploreDOM();
            }}
            placeholder="https://example.com"
            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => handleExploreDOM()}
            disabled={loading}
            className="px-3.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-blue-600" : ""}`} />
            <span>Refresh DOM</span>
          </button>
          <button
            onClick={() => handleExploreDOM()}
            disabled={loading}
            className="px-4 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold flex items-center gap-1.5 shadow-xs transition disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Camera className="w-3.5 h-3.5" />}
            <span>Capture Snapshot</span>
          </button>
        </div>
      </div>

      {pageTitle && (
        <div className="flex items-center justify-between px-4 py-2 rounded-lg bg-blue-50/60 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-xs text-blue-900 dark:text-blue-200">
          <div className="flex items-center gap-2 truncate">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold truncate">Active Page:</span>
            <span className="truncate">{pageTitle}</span>
          </div>
          <span className="font-mono text-[10px] text-blue-600 dark:text-blue-400 shrink-0">
            {elements.length} elements inspected
          </span>
        </div>
      )}

      {/* 2. 3-PANEL DOM INSPECTOR (Left Tree, Center Viewport / Target Box, Right Properties) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: DOM Hierarchy List (4 cols) */}
        <div className="lg:col-span-4 p-4 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col h-[560px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <Code2 className="w-4 h-4 text-[#2563EB]" />
              <span>Accessibility DOM Hierarchy</span>
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">Agent Browser</span>
          </div>

          {/* Search & Filter */}
          <div className="py-2.5 space-y-2 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 text-xs text-slate-500 border border-slate-200 dark:border-slate-700">
              <Search className="w-3.5 h-3.5 shrink-0" />
              <input
                type="text"
                placeholder="Filter DOM elements..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-none focus:outline-none text-[11px] text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="flex items-center gap-1 text-[10px]">
              {(["interactive", "visible", "all"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t)}
                  className={`px-2 py-0.5 rounded capitalize font-medium transition ${
                    filterType === t
                      ? "bg-[#2563EB] text-white"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  {t}
                </button>
              ))}
              <span className="ml-auto text-slate-400 font-mono text-[10px]">
                {filteredElements.length}/{elements.length}
              </span>
            </div>
          </div>

          {/* Element Tree List */}
          <div className="flex-1 overflow-y-auto pt-2 space-y-1 scrollbar-thin">
            {loading && elements.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-2 text-slate-400">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                <p className="text-xs">Extracting live DOM tree...</p>
              </div>
            ) : filteredElements.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-2 text-slate-400">
                <Code2 className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                  {elements.length === 0 ? "No DOM tree loaded" : "No elements match filter"}
                </p>
                <p className="text-[11px] text-slate-400 max-w-xs">
                  {elements.length === 0
                    ? "Click 'Capture Snapshot' above to extract live page elements."
                    : "Switch filter to 'All' or adjust search query."}
                </p>
                {elements.length > 0 && filterType !== "all" && (
                  <button
                    onClick={() => setFilterType("all")}
                    className="mt-2 px-2.5 py-1 rounded bg-[#2563EB] text-white text-[10px] font-semibold"
                  >
                    View All {elements.length} Elements
                  </button>
                )}
              </div>
            ) : (
              filteredElements.map((el, idx) => {
                const originalIndex = elements.indexOf(el);
                const isSelected = selectedIdx === originalIndex;
                const idVal = el.element_id || el.stable_attributes?.id;
                const testId = el.stable_attributes?.["data-testid"];
                const label = el.accessible_name || el.text || "";

                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedIdx(originalIndex)}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg cursor-pointer transition text-xs ${
                      isSelected
                        ? "bg-[#2563EB] text-white font-semibold shadow-xs"
                        : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200"
                    }`}
                  >
                    <span
                      className={`font-mono text-[11px] font-bold ${
                        isSelected
                          ? "text-white"
                          : ["button", "input", "a", "select"].includes(el.tag)
                          ? "text-blue-600 dark:text-blue-400"
                          : "text-slate-700 dark:text-slate-300"
                      }`}
                    >
                      &lt;{el.tag}&gt;
                    </span>

                    {idVal && (
                      <span
                        className={`font-mono text-[10px] truncate max-w-[90px] ${
                          isSelected ? "text-blue-200" : "text-purple-600 dark:text-purple-400"
                        }`}
                      >
                        #{idVal}
                      </span>
                    )}

                    {testId && !idVal && (
                      <span
                        className={`font-mono text-[9px] px-1 rounded truncate max-w-[90px] ${
                          isSelected ? "bg-blue-800 text-white" : "bg-blue-50 dark:bg-blue-950/80 text-blue-600"
                        }`}
                      >
                        [{testId}]
                      </span>
                    )}

                    {el.role && (
                      <span
                        className={`font-mono text-[9px] px-1 rounded shrink-0 ${
                          isSelected
                            ? "bg-blue-800 text-white"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                        }`}
                      >
                        role={el.role}
                      </span>
                    )}

                    {label && (
                      <span
                        className={`text-[10px] truncate ml-auto max-w-[120px] ${
                          isSelected ? "text-blue-100" : "text-slate-400"
                        }`}
                      >
                        {label}
                      </span>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* CENTER: Bounding Viewport Element Preview (4 cols) */}
        <div className="lg:col-span-4 p-4 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col h-[560px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
              <Crosshair className="w-4 h-4 text-emerald-500" />
              <span>Target Viewport & Highlights</span>
            </h3>
            <span className="text-[10px] text-emerald-600 font-semibold font-mono truncate max-w-[140px]">
              {selectedElement ? `<${selectedElement.tag}>` : "No selection"}
            </span>
          </div>

          <div className="flex-1 bg-slate-950 rounded-xl flex flex-col items-center justify-center relative overflow-hidden my-2 shadow-inner">
            {screenshotUrl ? (
              <div className="w-full h-full relative overflow-auto flex items-center justify-center p-2">
                <div className="relative inline-block max-w-full max-h-full">
                  <img
                    ref={imgRef}
                    src={screenshotUrl}
                    alt="DOM Snapshot"
                    onLoad={updateImageScale}
                    onClick={handleViewportClick}
                    title="Click element in screenshot to select"
                    className="max-w-full max-h-[440px] rounded-lg object-contain shadow-md cursor-crosshair select-none"
                  />
                  {/* Highlight bounding box accurately scaled to image dimensions */}
                  {boxX !== null && boxY !== null && boxW !== null && boxH !== null && (
                    <div
                      className="absolute border-2 border-emerald-400 bg-emerald-400/20 shadow-lg pointer-events-none animate-pulse rounded"
                      style={{
                        left: `${boxX}px`,
                        top: `${boxY}px`,
                        width: `${boxW}px`,
                        height: `${boxH}px`,
                      }}
                    />
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-center p-6 space-y-3 text-slate-400">
                <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center text-slate-500">
                  <Camera className="w-6 h-6" />
                </div>
                <p className="text-xs font-semibold text-slate-300">No Viewport Snapshot</p>
                <p className="text-[11px] text-slate-500 max-w-xs">
                  Click 'Capture Snapshot' or enter a target URL to stream live visual DOM overlays and bounding boxes.
                </p>
              </div>
            )}

            <div className="absolute bottom-3 left-3 right-3 p-2 rounded-lg bg-slate-900/95 border border-slate-800 text-[10px] text-slate-300 font-mono flex items-center justify-between">
              <span>
                Bounding Rect: x={selectedElement?.box?.x ?? 0} y={selectedElement?.box?.y ?? 0} w=
                {selectedElement?.box?.width ?? 0} h={selectedElement?.box?.height ?? 0}
              </span>
              <span className="text-emerald-400 font-semibold">
                Visible: {selectedElement?.is_visible ? "true" : "false"}
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT: Element Properties Inspector (4 cols) */}
        <div className="lg:col-span-4 p-4 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col h-[560px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
              Element Properties
            </h3>
            {selectedElement && (
              <button
                onClick={() => handleCopy(candidateLocators[0]?.value || selectedElement.tag, "Locator")}
                className="text-[10px] text-[#2563EB] dark:text-blue-400 font-semibold flex items-center gap-1 hover:underline"
              >
                <Copy className="w-3 h-3" />
                <span>Copy Logical ID</span>
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 py-2 text-xs scrollbar-thin">
            {selectedElement ? (
              <>
                <div className="space-y-1">
                  <span className="font-semibold text-slate-500 text-[10px] uppercase">HTML Tag</span>
                  <p className="font-mono text-slate-900 dark:text-slate-100 font-bold">
                    &lt;{selectedElement.tag}&gt;
                  </p>
                </div>

                {selectedElement.role && (
                  <div className="space-y-1">
                    <span className="font-semibold text-slate-500 text-[10px] uppercase">ARIA Role</span>
                    <p className="font-mono text-blue-600 dark:text-blue-400 font-bold">{selectedElement.role}</p>
                  </div>
                )}

                {selectedElement.accessible_name && (
                  <div className="space-y-1">
                    <span className="font-semibold text-slate-500 text-[10px] uppercase">Accessible Name</span>
                    <p className="font-medium text-slate-800 dark:text-slate-200">{selectedElement.accessible_name}</p>
                  </div>
                )}

                {selectedElement.text && (
                  <div className="space-y-1">
                    <span className="font-semibold text-slate-500 text-[10px] uppercase">Text Content</span>
                    <p className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 font-mono text-[11px] line-clamp-3">
                      "{selectedElement.text.trim()}"
                    </p>
                  </div>
                )}

                <div className="space-y-1">
                  <span className="font-semibold text-slate-500 text-[10px] uppercase">Attributes Dictionary</span>
                  <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 font-mono text-[10px] space-y-1 max-h-36 overflow-y-auto">
                    {Object.keys(selectedElement.stable_attributes || {}).length === 0 &&
                    Object.keys(selectedElement.aria_properties || {}).length === 0 ? (
                      <span className="text-slate-400">No explicit attributes</span>
                    ) : (
                      <>
                        {Object.entries(selectedElement.stable_attributes || {}).map(([k, v]) => (
                          <div key={k} className="flex items-center justify-between">
                            <span className="text-slate-500">{k}:</span>
                            <span className="text-slate-800 dark:text-slate-200 font-semibold truncate max-w-[140px]">
                              "{v}"
                            </span>
                          </div>
                        ))}
                        {Object.entries(selectedElement.aria_properties || {}).map(([k, v]) => (
                          <div key={k} className="flex items-center justify-between">
                            <span className="text-blue-500">{k}:</span>
                            <span className="text-slate-800 dark:text-slate-200 font-semibold truncate max-w-[140px]">
                              "{v}"
                            </span>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="font-semibold text-slate-500 text-[10px] uppercase">Candidate Locators</span>
                  <div className="space-y-1.5 font-mono text-[10px]">
                    {candidateLocators.map((loc, idx) => (
                      <div
                        key={idx}
                        onClick={() => handleCopy(loc.value, loc.label)}
                        className={`p-2 rounded-lg flex items-center justify-between cursor-pointer hover:opacity-80 transition ${loc.color}`}
                        title="Click to copy selector"
                      >
                        <div className="truncate mr-2">
                          <span className="text-[9px] block uppercase font-bold opacity-75">{loc.label}</span>
                          <span className="font-bold truncate">{loc.value}</span>
                        </div>
                        <Copy className="w-3 h-3 shrink-0 opacity-60" />
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-2 text-slate-400">
                <Crosshair className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">No Element Selected</p>
                <p className="text-[11px] text-slate-400">
                  Select any element from the DOM tree on the left to inspect its tag, attributes, and candidate locators.
                </p>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={handleSaveProfile}
              disabled={!selectedElement}
              className="w-full py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition disabled:opacity-50"
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
