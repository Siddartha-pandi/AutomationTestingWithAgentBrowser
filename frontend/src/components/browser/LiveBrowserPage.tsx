"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Compass,
  Play,
  Square,
  RefreshCw,
  Camera,
  Globe,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Lock,
  ExternalLink,
  Laptop,
  Loader2,
  Maximize2,
} from "lucide-react";
import { browserApi } from "@/api";
import { useToast } from "../common/ToastProvider";
import { NavView } from "../layout/AppShell";

interface LiveBrowserPageProps {
  projectId: string;
  onNavigate: (view: NavView) => void;
}

export function LiveBrowserPage({ projectId, onNavigate }: LiveBrowserPageProps) {
  const [sessionActive, setSessionActive] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [currentUrl, setCurrentUrl] = useState("");
  const [inputUrl, setInputUrl] = useState("https://mahila-action-vsk.vercel.app/home?modal=login");
  const [browserStatus, setBrowserStatus] = useState<"Connected" | "Navigating" | "Idle" | "Terminated">("Idle");
  const [viewportScreenshot, setViewportScreenshot] = useState<string | null>(null);
  const [browserLogs, setBrowserLogs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sessionIdRef = useRef<string>("");
  const logsEndRef = useRef<HTMLDivElement | null>(null);
  const { success, error, warning, info } = useToast();

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Clean up session on unmount
  useEffect(() => {
    return () => {
      if (sessionIdRef.current) {
        browserApi.close(sessionIdRef.current).catch(() => {});
      }
    };
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [browserLogs]);

  const addLog = (tag: string, message: string) => {
    const time = new Date().toLocaleTimeString();
    setBrowserLogs((prev) => [...prev, `[${time}] [${tag}] ${message}`]);
  };

  const ensureSession = async (): Promise<string> => {
    if (sessionActive && sessionIdRef.current) {
      return sessionIdRef.current;
    }
    setIsLoading(true);
    addLog("SESSION", "Spawning new isolated Agent Browser CLI process...");
    try {
      const res = await browserApi.launch({
        project_id: projectId || undefined,
        allowed_domains: ["*"],
      });
      const newId = res.session_id;
      setSessionId(newId);
      sessionIdRef.current = newId;
      setSessionActive(true);
      setBrowserStatus("Connected");
      addLog("SESSION", `Isolated Agent Browser session initialized (${newId}).`);
      success("Browser Started", `Session ${newId} ready.`);
      return newId;
    } catch (err: any) {
      addLog("ERROR", `Failed to launch browser: ${err.message}`);
      error("Launch Error", err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartSession = async () => {
    try {
      await ensureSession();
    } catch {
      // Error handled in ensureSession
    }
  };

  const handleStopSession = async () => {
    if (!sessionId) return;
    setIsLoading(true);
    addLog("SESSION", `Terminating session ${sessionId}...`);
    try {
      await browserApi.close(sessionId);
      setSessionActive(false);
      setSessionId("");
      sessionIdRef.current = "";
      setBrowserStatus("Terminated");
      setViewportScreenshot(null);
      addLog("SESSION", "Agent Browser CLI subprocess exited cleanly.");
      warning("Session Terminated", "Browser process closed.");
    } catch (err: any) {
      addLog("ERROR", `Error closing session: ${err.message}`);
      error("Close Error", err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNavigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    let target = inputUrl.trim();
    if (!target) return;
    if (!target.startsWith("http://") && !target.startsWith("https://")) {
      target = `https://${target}`;
      setInputUrl(target);
    }

    try {
      setIsLoading(true);
      const activeId = await ensureSession();

      setBrowserStatus("Navigating");
      addLog("NAVIGATE", `Navigating to ${target}...`);
      info("Navigating", `Requesting ${target}...`);

      const res = await browserApi.navigate(activeId, target, 35);

      setCurrentUrl(target);
      setBrowserStatus("Connected");

      if (res.image_base64) {
        setViewportScreenshot(res.image_base64);
        addLog("VIEWPORT", `Live frame rendered (${target}).`);
      } else {
        // Fallback: request screenshot explicitly
        try {
          const shot = await browserApi.screenshot(activeId);
          if (shot.image_base64) {
            setViewportScreenshot(shot.image_base64);
            addLog("VIEWPORT", `Live frame captured via snapshot.`);
          }
        } catch {
          // Ignore fallback error
        }
      }

      addLog("NAVIGATE", `Page loaded: ${target} (${res.duration_ms ? `${res.duration_ms}ms` : "HTTP 200"}).`);
      success("Page Loaded", `Viewport updated for ${target}`);
    } catch (err: any) {
      setBrowserStatus("Connected");
      addLog("ERROR", `Navigation failed: ${err.message}`);
      error("Navigation Failed", err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTakeScreenshot = async () => {
    if (!sessionId) {
      error("No Active Session", "Please start or navigate first.");
      return;
    }
    setIsLoading(true);
    addLog("SCREENSHOT", "Requesting full viewport frame from agent-browser...");
    try {
      const res = await browserApi.screenshot(sessionId, { full_page: false });
      if (res.image_base64) {
        setViewportScreenshot(res.image_base64);
      }
      addLog("SCREENSHOT", `Captured live viewport frame (${res.file_size || 0} bytes).`);
      success("Screenshot Captured", "Viewport frame refreshed.");
    } catch (err: any) {
      addLog("ERROR", `Screenshot failed: ${err.message}`);
      error("Screenshot Failed", err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Compass className="w-5 h-5 text-[#2563EB]" />
            <span>Live Browser Monitor</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Direct subprocess controller and live screenshot observer powered by Agent Browser CLI.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {sessionActive ? (
            <button
              onClick={handleStopSession}
              disabled={isLoading}
              className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition disabled:opacity-50 cursor-pointer"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Stop Session</span>
            </button>
          ) : (
            <button
              onClick={handleStartSession}
              disabled={isLoading}
              className="px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition disabled:opacity-50 cursor-pointer"
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              <span>Start Session</span>
            </button>
          )}

          <button
            onClick={handleTakeScreenshot}
            disabled={!sessionActive || isLoading}
            className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-700 transition disabled:opacity-40 cursor-pointer"
          >
            <Camera className="w-4 h-4 text-purple-500" />
            <span>Capture Screenshot</span>
          </button>
        </div>
      </div>

      {/* URL Navigation Bar */}
      <div className="p-4 rounded-xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs">
        <form onSubmit={handleNavigate} className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-2 flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100">
            <Lock className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <input
              type="text"
              required
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full bg-transparent border-none focus:outline-none font-mono text-xs"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white font-semibold flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer"
          >
            {isLoading && browserStatus === "Navigating" ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : null}
            <span>Navigate</span>
          </button>

          <button
            type="button"
            onClick={() => handleNavigate()}
            disabled={isLoading || !currentUrl}
            className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition disabled:opacity-40 cursor-pointer"
            title="Refresh Page"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>

          {currentUrl && (
            <a
              href={currentUrl}
              target="_blank"
              rel="noreferrer"
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
              title="Open Target in New Tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </form>

        <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
          <span>
            Current Target:{" "}
            <strong className="text-slate-700 dark:text-slate-300 font-mono">
              {currentUrl || "None"}
            </strong>
          </span>
          <span className="font-mono">
            Session ID:{" "}
            <strong className="text-blue-600">{sessionId || "Disconnected"}</strong>
          </span>
        </div>
      </div>

      {/* Main Viewport & Console Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Browser Viewport Preview (2 cols) */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Laptop className="w-4 h-4 text-[#2563EB]" />
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
                Agent Browser Viewport (1280x800)
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  sessionActive ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
                }`}
              />
              <span className="text-[11px] font-mono font-semibold capitalize text-slate-700 dark:text-slate-300">
                {browserStatus}
              </span>
            </div>
          </div>

          <div className="w-full aspect-video rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex items-center justify-center relative shadow-inner">
            {isLoading && (
              <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-2xs flex flex-col items-center justify-center gap-2 z-10 animate-in fade-in">
                <Loader2 className="w-7 h-7 text-[#2563EB] animate-spin" />
                <span className="text-xs font-mono text-slate-300">
                  {browserStatus === "Navigating" ? "Navigating and rendering DOM..." : "Capturing viewport..."}
                </span>
              </div>
            )}

            {viewportScreenshot ? (
              <img
                src={viewportScreenshot}
                alt="Live Viewport Capture"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-8 space-y-2">
                <Compass className="w-8 h-8 text-slate-600 mx-auto" />
                <div className="text-slate-400 text-xs font-medium">
                  Browser session idle.
                </div>
                <div className="text-slate-600 text-[11px]">
                  Click <strong>Navigate</strong> above to launch and view the live DOM rendering.
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Browser Logs & Diagnostic Info (1 col) */}
        <div className="p-5 rounded-2xl bg-white dark:bg-[#161F30] border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-purple-500" />
              <h3 className="font-bold text-xs text-slate-900 dark:text-slate-100">
                CLI Activity Logs
              </h3>
            </div>
            <button
              onClick={() => setBrowserLogs([])}
              className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
            >
              Clear
            </button>
          </div>

          <div className="flex-1 bg-slate-950 rounded-xl p-3 font-mono text-[11px] text-slate-300 overflow-y-auto max-h-96 min-h-[300px] space-y-1.5 scrollbar-thin">
            {browserLogs.length === 0 ? (
              <div className="text-slate-600 italic">No activity logs recorded yet.</div>
            ) : (
              browserLogs.map((log, index) => (
                <div key={index} className="leading-tight break-all">
                  {log}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>

          {/* Zero-AI Note */}
          <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-[10px] text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>Pure subprocess isolation. No external telemetry or cloud renderers.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
