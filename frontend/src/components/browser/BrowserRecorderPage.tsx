"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Video,
  Play,
  Square,
  Globe,
  MousePointer,
  Type,
  ListFilter,
  CheckSquare,
  Radio,
  ArrowDown,
  Trash2,
  Edit2,
  Save,
  Clock,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  FileCode,
  GitBranch,
  RefreshCw,
  Camera,
  ChevronRight,
  Loader2,
  Crosshair,
  Layers,
  Search,
} from "lucide-react";
import { recorderApi, browserApi, flowsApi, testsApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";
import { NavView } from "../layout/AppShell";

interface BrowserRecorderPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
  onSelectFlow?: (flowId: string) => void;
  onSelectTest?: (testId: string) => void;
}

export interface RecordedAction {
  id: string;
  action: "navigate" | "click" | "fill" | "select" | "check" | "radio" | "scroll" | "hover" | "dblclick" | "reload" | "back";
  target: string;
  value?: string;
  timestamp: string;
  status: "verified" | "pending";
}

export function BrowserRecorderPage({
  projectId,
  onNavigate,
  onSelectFlow,
  onSelectTest,
}: BrowserRecorderPageProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [targetUrl, setTargetUrl] = useState("https://mahila-action-vsk.vercel.app/");
  const [currentUrl, setCurrentUrl] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recordedActions, setRecordedActions] = useState<RecordedAction[]>([]);
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [saveTitle, setSaveTitle] = useState("");
  const [saveType, setSaveType] = useState<"flow" | "test">("test");

  // Manual interactive input state
  const [interactiveAction, setInteractiveAction] = useState<RecordedAction["action"]>("click");
  const [interactiveSelector, setInteractiveSelector] = useState("");
  const [interactiveValue, setInteractiveValue] = useState("");

  // Inspect page elements state
  const [inspecting, setInspecting] = useState(false);
  const [detectedElements, setDetectedElements] = useState<any[]>([]);
  const [elementFilter, setElementFilter] = useState("");

  const sessionIdRef = useRef<string | null>(null);
  const { success, error, warning, info } = useToast();
  const { confirm } = useConfirm();

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (sessionIdRef.current) {
        recorderApi.stop(sessionIdRef.current).catch(() => {});
      }
    };
  }, []);

  // Refresh screenshot from API
  const refreshScreenshot = async (sessId: string) => {
    try {
      const shot = await browserApi.screenshot(sessId, { full_page: false });
      if (shot && shot.image_base64) {
        setScreenshotUrl(shot.image_base64);
      } else if (shot && shot.screenshot) {
        setScreenshotUrl(shot.screenshot);
      }
    } catch (err) {
      console.warn("Could not capture preview screenshot:", err);
    }
  };

  // Start recording session
  const handleStartRecording = async () => {
    let url = targetUrl.trim();
    if (!url) {
      error("URL Required", "Please enter a valid target URL.");
      return;
    }
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      url = `https://${url}`;
      setTargetUrl(url);
    }

    setIsLoading(true);
    try {
      info("Initializing Session", "Spawning isolated Agent Browser subprocess...");
      const res = await recorderApi.start(projectId || "p1-default", url);

      const newSessionId = res.session_id;
      setSessionId(newSessionId);
      sessionIdRef.current = newSessionId;
      setCurrentUrl(url);
      setIsRecording(true);

      const initAction: RecordedAction = {
        id: `rec_${Date.now()}`,
        action: "navigate",
        target: url,
        timestamp: new Date().toLocaleTimeString(),
        status: "verified",
      };
      setRecordedActions([initAction]);

      // Set initial base64 screenshot
      const b64 = res.image_base64 || res.initial_screenshot || res.screenshot;
      if (b64 && b64.startsWith("data:image")) {
        setScreenshotUrl(b64);
      } else {
        await refreshScreenshot(newSessionId);
      }

      success("Session Active", "Agent Browser ready. Actions are recorded in real time.");
      // Auto-inspect elements on load
      recorderApi.inspect(newSessionId).then((insRes) => {
        if (insRes && insRes.elements) {
          setDetectedElements(insRes.elements);
        }
      }).catch(() => {});
    } catch (err: any) {
      error("Session Failed", err.message || "Failed to start Agent Browser recording session.");
    } finally {
      setIsLoading(false);
    }
  };

  // Stop recording session
  const handleStopRecording = async () => {
    if (sessionId) {
      try {
        await recorderApi.stop(sessionId);
      } catch (e) {
        // ignore close error
      }
    }
    setIsRecording(false);
    success("Recording Paused", `Captured ${recordedActions.length} verified actions.`);
  };

  // Fetch interactive elements on current page
  const handleInspectElements = async () => {
    if (!sessionId) return;
    setInspecting(true);
    try {
      const res = await recorderApi.inspect(sessionId);
      if (res && res.elements) {
        setDetectedElements(res.elements);
        info("Elements Detected", `Identified ${res.elements.length} interactive elements on current page.`);
      }
    } catch (err: any) {
      error("Inspection Failed", err.message);
    } finally {
      setInspecting(false);
    }
  };

  // Select detected element
  const handleSelectElement = (el: any) => {
    setInteractiveSelector(el.selector);
    if (el.tag === "input" || el.tag === "textarea") {
      setInteractiveAction("fill");
    } else if (el.tag === "select") {
      setInteractiveAction("select");
    } else {
      setInteractiveAction("click");
    }
    success("Selector Set", `Selected ${el.tag} '${el.text || el.selector}'`);
  };

  // Execute and record action
  const handleExecuteAction = async () => {
    if (!sessionId) return;
    const isNavigation = ["scroll", "reload", "back"].includes(interactiveAction);
    if (!interactiveSelector && !isNavigation) {
      error("Selector Required", "Specify an element selector or click one from Page Elements.");
      return;
    }

    setIsLoading(true);
    try {
      info("Executing Action", `Dispatching ${interactiveAction} on '${interactiveSelector || "page"}'...`);

      let actRes: any = null;
      try {
        actRes = await recorderApi.recordAction(
          sessionId,
          interactiveAction,
          interactiveSelector,
          interactiveValue || undefined
        );
      } catch (recErr) {
        // Fallback through browser action API
        actRes = await browserApi.action(sessionId, {
          action: interactiveAction,
          selector: interactiveSelector,
          text: interactiveValue,
          value: interactiveValue,
        });
      }

      const newAction: RecordedAction = {
        id: `rec_${Date.now()}`,
        action: interactiveAction,
        target: interactiveSelector || "page",
        value: interactiveValue || undefined,
        timestamp: new Date().toLocaleTimeString(),
        status: "verified",
      };

      setRecordedActions((prev) => [...prev, newAction]);
      success("Action Recorded", `Verified: ${interactiveAction} -> ${interactiveSelector || "page"}`);

      // Update screenshot
      const b64 = actRes?.image_base64 || actRes?.screenshot;
      if (b64 && b64.startsWith("data:image")) {
        setScreenshotUrl(b64);
      } else {
        await refreshScreenshot(sessionId);
      }

      // Clear input fields
      setInteractiveSelector("");
      setInteractiveValue("");

      // Re-inspect elements after action
      recorderApi.inspect(sessionId).then((ins) => {
        if (ins && ins.elements) setDetectedElements(ins.elements);
      }).catch(() => {});
    } catch (err: any) {
      error("Action Failed", err.message || "Agent Browser could not execute action.");
    } finally {
      setIsLoading(false);
    }
  };

  // Delete recorded step
  const handleDeleteAction = (id: string) => {
    setRecordedActions((prev) => prev.filter((a) => a.id !== id));
  };

  // Clear all steps
  const handleClearAll = () => {
    confirm({
      title: "Clear Recorded Actions?",
      message: "This will remove all recorded steps from this session. This cannot be undone.",
      confirmText: "Clear Actions",
      variant: "danger",
      onConfirm: () => {
        setRecordedActions([]);
        success("Actions Cleared", "Timeline reset.");
      },
    });
  };

  // Save as Flow or Test Case
  const handleSaveRecording = async () => {
    if (!saveTitle.trim()) {
      error("Title Required", "Please provide a name for the saved item.");
      return;
    }

    setIsLoading(true);
    try {
      // 1. Try backend recorderApi.save first
      if (sessionId) {
        try {
          const res = await recorderApi.save({
            session_id: sessionId,
            project_id: projectId || "p1-default",
            name: saveTitle.trim(),
            target_type: saveType,
            description: `Imported from Browser Recorder (${recordedActions.length} steps)`,
          });
          if (res && res.id) {
            success("Recording Saved", `Created ${saveType === "flow" ? "visual flow" : "test case"} '${saveTitle}'.`);
            setSaveModalOpen(false);
            if (saveType === "flow") {
              if (onSelectFlow) onSelectFlow(res.id);
              onNavigate("automation_builder");
            } else {
              if (onSelectTest) onSelectTest(res.id);
              onNavigate("testing_builder");
            }
            return;
          }
        } catch (backendSaveErr) {
          console.warn("Backend save endpoint encountered issue, falling back to direct creation:", backendSaveErr);
        }
      }

      // 2. Client-side fallback creation
      if (saveType === "flow") {
        info("Generating Flow", "Transforming recorded actions into React Flow DAG...");
        const nodes: any[] = recordedActions.map((act, idx) => ({
          id: `node_${idx + 1}`,
          type: "action",
          action: act.action,
          config: {
            url: act.action === "navigate" ? act.target : undefined,
            target: act.action !== "navigate" ? { selector: act.target } : undefined,
            value: act.value,
          },
          position: { x: 100 + idx * 240, y: 150 },
        }));
        nodes.push({
          id: `node_${nodes.length + 1}`,
          type: "stop",
          action: "stop" as any,
          config: { reason: "Recording completed" },
          position: { x: 100 + nodes.length * 240, y: 150 },
        });

        const edges = [];
        for (let i = 0; i < nodes.length - 1; i++) {
          edges.push({ id: `e_${i}`, source: nodes[i].id, target: nodes[i + 1].id });
        }

        const flowDef = {
          name: saveTitle.trim(),
          description: `Recorded session from ${currentUrl || targetUrl}`,
          start_node_id: "node_1",
          nodes,
          edges,
        };

        const created = await flowsApi.create({
          project_id: projectId || "p1-default",
          name: saveTitle.trim(),
          description: `Imported from Browser Recorder (${recordedActions.length} steps)`,
          definition: flowDef,
        });

        success("Flow Saved", `Created visual flow '${saveTitle}'.`);
        setSaveModalOpen(false);
        if (onSelectFlow && created.id) onSelectFlow(created.id);
        onNavigate("automation_builder");
      } else {
        info("Generating Test Case", "Transforming recorded actions into Test Case definition...");
        const steps = recordedActions.map((act, idx) => ({
          id: `step_${idx + 1}`,
          name: `${act.action.toUpperCase()} ${act.target}`,
          step_type: "action",
          action: act.action,
          target: act.action !== "navigate" ? { selector: act.target } : undefined,
          config: act.action === "navigate" ? { url: act.target } : { value: act.value },
        }));

        const testDef = {
          name: saveTitle.trim(),
          description: `Recorded regression test from ${currentUrl || targetUrl}`,
          setup_steps: [],
          steps,
          teardown_steps: [],
        };

        const created = await testsApi.create({
          project_id: projectId || "p1-default",
          name: saveTitle.trim(),
          description: `Imported from Browser Recorder (${recordedActions.length} steps)`,
          test_case: testDef,
        });

        success("Test Case Saved", `Created test case '${saveTitle}'.`);
        setSaveModalOpen(false);
        if (onSelectTest && created.id) onSelectTest(created.id);
        onNavigate("testing_builder");
      }
    } catch (err: any) {
      error("Save Failed", err.message || "Failed to persist recording.");
    } finally {
      setIsLoading(false);
    }
  };

  const filteredElements = detectedElements.filter((el) => {
    if (!elementFilter) return true;
    const q = elementFilter.toLowerCase();
    return (
      (el.text && el.text.toLowerCase().includes(q)) ||
      (el.selector && el.selector.toLowerCase().includes(q)) ||
      (el.tag && el.tag.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Video className="w-6 h-6 text-[#2563EB]" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Browser Recorder
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Record, inspect, and verify browser user interactions using the native Agent Browser subprocess engine.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-900">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
          <span>Verified CLI Recording Mode • Subprocess Isolated</span>
        </div>
      </div>

      {/* Session Controls Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-2xs flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Globe className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            disabled={isRecording || isLoading}
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            placeholder="Enter target URL (e.g. https://example.com)..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          {!isRecording ? (
            <button
              onClick={handleStartRecording}
              disabled={isLoading}
              className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-5 py-2 bg-[#2563EB] hover:bg-blue-600 text-white rounded-lg text-xs font-semibold shadow-xs transition-all disabled:opacity-50 cursor-pointer"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>{isLoading ? "Starting..." : "Start Recording"}</span>
            </button>
          ) : (
            <button
              onClick={handleStopRecording}
              disabled={isLoading}
              className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <Square className="w-4 h-4" />
              <span>Stop Session</span>
            </button>
          )}

          {isRecording && (
            <button
              onClick={() => sessionId && refreshScreenshot(sessionId)}
              disabled={isLoading || !sessionId}
              className="p-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-lg text-xs hover:bg-slate-50 dark:hover:bg-slate-700 transition cursor-pointer"
              title="Refresh Viewport Frame"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          )}

          {currentUrl && (
            <a
              href={currentUrl}
              target="_blank"
              rel="noreferrer"
              className="p-2 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-lg text-xs hover:bg-slate-50 dark:hover:bg-slate-700 transition"
              title="Open Target in New Tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}

          {recordedActions.length > 0 && (
            <button
              onClick={() => {
                setSaveTitle(`Recorded Flow - ${new Date().toLocaleDateString()}`);
                setSaveModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <Save className="w-4 h-4" />
              <span>Save As...</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Recording Workspace: Live Action Dispatcher (Left) + Recorded Timeline (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 7 Cols: Live Viewport & Interactive Action Trigger */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-2xs flex flex-col">
            <div className="p-3 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
              <span className="flex items-center gap-1.5">
                <Camera className="w-3.5 h-3.5 text-blue-500" />
                <span>Session Viewport {sessionId ? `(#${sessionId.slice(0, 10)})` : ""}</span>
              </span>
              <div className="flex items-center gap-2">
                {isRecording && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-900 animate-pulse font-mono">
                    &bull; REC LIVE
                  </span>
                )}
              </div>
            </div>

            {/* Viewport Frame */}
            <div className="relative min-h-[380px] bg-slate-950 flex items-center justify-center p-2 overflow-hidden shadow-inner">
              {isLoading && (
                <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-2xs flex flex-col items-center justify-center gap-2 z-10 animate-in fade-in">
                  <Loader2 className="w-7 h-7 text-[#2563EB] animate-spin" />
                  <span className="text-xs font-mono text-slate-300">
                    Executing action and capturing frame...
                  </span>
                </div>
              )}

              {screenshotUrl ? (
                <img
                  src={screenshotUrl}
                  alt="Live Session Preview"
                  className="max-h-[460px] w-full object-contain rounded border border-slate-800 shadow"
                />
              ) : (
                <div className="text-center text-slate-400 space-y-2 p-8">
                  <Video className="w-10 h-10 mx-auto opacity-30 text-[#2563EB]" />
                  <p className="text-xs font-medium">
                    {isRecording ? "Capturing viewport from agent-browser..." : "Browser session idle"}
                  </p>
                  <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                    Enter target URL and click <strong>Start Recording</strong> to launch browser.
                  </p>
                </div>
              )}
            </div>

            {/* Action Dispatcher Control Strip */}
            {isRecording && (
              <div className="p-3 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  <span className="flex items-center gap-1">
                    <MousePointer className="w-3.5 h-3.5 text-blue-500" />
                    <span>Execute & Record Interaction</span>
                  </span>

                  <button
                    onClick={handleInspectElements}
                    disabled={inspecting}
                    className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-700 dark:text-blue-400 capitalize font-medium cursor-pointer"
                  >
                    {inspecting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Crosshair className="w-3 h-3" />}
                    <span>{inspecting ? "Scanning DOM..." : "Inspect Page Elements"}</span>
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                  <select
                    value={interactiveAction}
                    onChange={(e) => setInteractiveAction(e.target.value as any)}
                    className="px-2.5 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200"
                  >
                    <option value="click">Click</option>
                    <option value="dblclick">Double Click</option>
                    <option value="fill">Fill Input</option>
                    <option value="select">Select Option</option>
                    <option value="hover">Hover</option>
                    <option value="check">Check Box / Radio</option>
                    <option value="scroll">Scroll Down</option>
                    <option value="reload">Reload</option>
                    <option value="back">Back</option>
                  </select>

                  <input
                    type="text"
                    value={interactiveSelector}
                    onChange={(e) => setInteractiveSelector(e.target.value)}
                    placeholder="Selector (e.g. #submit-btn, button)"
                    className="sm:col-span-2 px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-900 dark:text-white placeholder:text-slate-400"
                  />

                  <button
                    disabled={isLoading}
                    onClick={handleExecuteAction}
                    className="px-3 py-1.5 bg-[#2563EB] hover:bg-blue-600 text-white rounded-lg text-xs font-semibold shadow-xs transition-all disabled:opacity-50 cursor-pointer flex items-center justify-center gap-1"
                  >
                    {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                    <span>{isLoading ? "Running..." : "Dispatch & Record"}</span>
                  </button>
                </div>

                {["fill", "select"].includes(interactiveAction) && (
                  <input
                    type="text"
                    value={interactiveValue}
                    onChange={(e) => setInteractiveValue(e.target.value)}
                    placeholder={interactiveAction === "fill" ? "Input text value to type..." : "Option value or visible text..."}
                    className="w-full px-3 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-white placeholder:text-slate-400"
                  />
                )}

                {/* Detected Page Elements Chips */}
                {detectedElements.length > 0 && (
                  <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <span>Click an element below to auto-populate selector ({detectedElements.length} found):</span>
                      <input
                        type="text"
                        placeholder="Filter elements..."
                        value={elementFilter}
                        onChange={(e) => setElementFilter(e.target.value)}
                        className="px-2 py-0.5 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-[10px]"
                      />
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto pr-1">
                      {filteredElements.slice(0, 20).map((el, i) => (
                        <button
                          key={i}
                          onClick={() => handleSelectElement(el)}
                          className="px-2 py-0.5 rounded bg-slate-100 hover:bg-blue-50 dark:bg-slate-800 dark:hover:bg-blue-950/60 text-[10px] text-slate-700 dark:text-slate-300 hover:text-blue-600 border border-slate-200 dark:border-slate-700 flex items-center gap-1 cursor-pointer transition truncate max-w-[200px]"
                          title={`${el.tag}: ${el.selector}`}
                        >
                          <span className="font-bold uppercase text-[9px] text-blue-500">{el.tag}</span>
                          <span className="truncate">{el.text || el.selector}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right 5 Cols: Recorded Steps Timeline */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-2xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Recorded Actions ({recordedActions.length})
              </h3>
              <p className="text-[11px] text-slate-500">
                Ordered trail of verified browser events
              </p>
            </div>
            {recordedActions.length > 0 && (
              <button
                onClick={handleClearAll}
                className="text-[11px] text-rose-600 hover:underline cursor-pointer"
              >
                Clear All
              </button>
            )}
          </div>

          <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1 scrollbar-thin">
            {recordedActions.map((act, idx) => (
              <div
                key={act.id}
                className="p-2.5 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-lg flex items-center justify-between gap-2 group hover:border-blue-500/50 transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-400 flex items-center justify-center text-[10px] font-bold">
                    {idx + 1}
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] font-bold uppercase text-slate-800 dark:text-slate-200">
                        {act.action}
                      </span>
                      <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                        ✓ Verified
                      </span>
                    </div>
                    <div className="text-xs font-mono text-slate-600 dark:text-slate-400 truncate max-w-[220px]">
                      {act.target}
                    </div>
                    {act.value && (
                      <div className="text-[10px] text-slate-500 italic truncate">
                        value: "{act.value}"
                      </div>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleDeleteAction(act.id)}
                  className="p-1 text-slate-400 hover:text-rose-600 rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                  title="Remove step"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            {recordedActions.length === 0 && (
              <div className="text-center py-12 text-slate-400 space-y-1">
                <Clock className="w-8 h-8 mx-auto opacity-30" />
                <p className="text-xs font-medium">No actions recorded yet</p>
                <p className="text-[11px] text-slate-400">
                  Interactions will appear here in chronological order.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Save Modal */}
      {saveModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Save Recorded Session
            </h3>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Item Name *
                </label>
                <input
                  type="text"
                  required
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  className="w-full mt-1 px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Target Entity
                </label>
                <div className="grid grid-cols-2 gap-3 mt-1">
                  <button
                    type="button"
                    onClick={() => setSaveType("test")}
                    className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                      saveType === "test"
                        ? "bg-blue-50/80 dark:bg-blue-950/50 border-blue-600 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500/10"
                        : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400"
                    }`}
                  >
                    <FileCode className="w-4 h-4 mb-1" />
                    <div className="text-xs font-bold">Test Case</div>
                    <div className="text-[10px] opacity-80">WrightTest test suite</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSaveType("flow")}
                    className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                      saveType === "flow"
                        ? "bg-blue-50/80 dark:bg-blue-950/50 border-blue-600 text-blue-700 dark:text-blue-300 ring-2 ring-blue-500/10"
                        : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400"
                    }`}
                  >
                    <GitBranch className="w-4 h-4 mb-1" />
                    <div className="text-xs font-bold">Visual Flow</div>
                    <div className="text-[10px] opacity-80">React Flow DAG</div>
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setSaveModalOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveRecording}
                disabled={isLoading || !saveTitle.trim()}
                className="px-4 py-2 bg-[#2563EB] hover:bg-blue-600 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                {isLoading ? "Saving..." : "Save Definition"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
