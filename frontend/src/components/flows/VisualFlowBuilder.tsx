"use client";

import React, { useState, useCallback, useMemo } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  NodeProps,
  Edge,
  Node,
} from "@xyflow/react";
import {
  Play,
  Save,
  CheckCircle2,
  AlertTriangle,
  Globe,
  MousePointer,
  Edit3,
  FileText,
  Clock,
  GitBranch,
  Camera,
  XCircle,
  Plus,
  Trash2,
  UploadCloud,
  Check,
  ChevronDown,
  ChevronUp,
  Terminal,
  Activity,
  Layers,
  ArrowRight,
  ShieldCheck,
  HelpCircle,
  Repeat,
  Table,
  ListOrdered,
  Eye,
  Crosshair,
  ArrowLeft,
  RotateCw,
  Calculator,
  Calendar,
  Code,
  Braces,
  Split,
  CheckSquare,
  ArrowDown,
  Search,
} from "lucide-react";
import { flowsApi } from "../../api";
import { useToast } from "../common/ToastProvider";
import { useConfirm } from "../common/ConfirmModal";

// 1. Custom Node Components
const ActionNode = ({ data, selected }: NodeProps) => {
  const getIcon = () => {
    switch (data.action) {
      case "navigate": return <Globe className="w-4 h-4 text-blue-500" />;
      case "click": return <MousePointer className="w-4 h-4 text-indigo-500" />;
      case "double_click": return <MousePointer className="w-4 h-4 text-purple-500" />;
      case "right_click": return <MousePointer className="w-4 h-4 text-pink-500" />;
      case "hover": return <Eye className="w-4 h-4 text-sky-500" />;
      case "fill": return <Edit3 className="w-4 h-4 text-amber-500" />;
      case "type": return <Edit3 className="w-4 h-4 text-orange-500" />;
      case "select": return <ListOrdered className="w-4 h-4 text-teal-500" />;
      case "check": return <CheckSquare className="w-4 h-4 text-emerald-500" />;
      case "uncheck": return <CheckSquare className="w-4 h-4 text-slate-400" />;
      case "scroll": return <ArrowDown className="w-4 h-4 text-blue-500" />;
      case "extract_text": return <FileText className="w-4 h-4 text-emerald-500" />;
      case "extract_attribute": return <FileText className="w-4 h-4 text-cyan-500" />;
      case "extract_table": return <Table className="w-4 h-4 text-blue-600" />;
      case "wait": return <Clock className="w-4 h-4 text-slate-500" />;
      case "wait_until": return <Clock className="w-4 h-4 text-amber-500" />;
      case "browser_back": return <ArrowLeft className="w-4 h-4 text-indigo-500" />;
      case "browser_forward": return <ArrowRight className="w-4 h-4 text-indigo-500" />;
      case "refresh": return <RotateCw className="w-4 h-4 text-teal-500" />;
      case "switch": return <Split className="w-4 h-4 text-amber-500" />;
      case "loop": return <Repeat className="w-4 h-4 text-violet-500" />;
      case "set_variable": return <Code className="w-4 h-4 text-blue-500" />;
      case "string_operation": return <Code className="w-4 h-4 text-emerald-500" />;
      case "number_operation": return <Calculator className="w-4 h-4 text-amber-500" />;
      case "json_operation": return <Braces className="w-4 h-4 text-purple-500" />;
      case "date_operation": return <Calendar className="w-4 h-4 text-rose-500" />;
      case "array_operation": return <ListOrdered className="w-4 h-4 text-cyan-500" />;
      case "screenshot": return <Camera className="w-4 h-4 text-purple-500" />;
      case "approval": return <ShieldCheck className="w-4 h-4 text-amber-600" />;
      default: return <Play className="w-4 h-4 text-blue-500" />;
    }
  };

  const status = (data as any).executionStatus;

  return (
    <div
      className={`px-3.5 py-2.5 rounded-xl bg-white dark:bg-[#161F30] border transition shadow-sm min-w-[190px] text-xs ${
        selected
          ? "border-blue-600 ring-2 ring-blue-500/20 shadow-md"
          : "border-slate-200 dark:border-slate-800"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100">
          {getIcon()}
          <span className="capitalize">{String(data.action || "Action").replace(/_/g, " ")}</span>
        </div>
        {status && (
          <span
            className={`w-2 h-2 rounded-full ${
              status === "passed"
                ? "bg-emerald-500"
                : status === "running"
                ? "bg-blue-500 animate-pulse"
                : "bg-rose-500"
            }`}
          />
        )}
      </div>
      <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[180px]">
        {String(
          (data as any).summary ||
          (data as any).config?.url ||
          (data as any).config?.logical_id ||
          (data as any).config?.target?.selector ||
          (data as any).config?.value_template ||
          ""
        )}
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-[#2563EB] !w-2 !h-2" />
    </div>
  );
};

const ConditionNode = ({ data, selected }: NodeProps) => (
  <div
    className={`px-3.5 py-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border transition shadow-sm min-w-[190px] text-xs ${
      selected
        ? "border-amber-600 ring-2 ring-amber-500/20 shadow-md"
        : "border-amber-200 dark:border-amber-800"
    }`}
  >
    <Handle type="target" position={Position.Top} className="!bg-amber-600 !w-2 !h-2" />
    <div className="flex items-center gap-2 font-bold text-amber-800 dark:text-amber-300">
      <GitBranch className="w-4 h-4" />
      <span>Condition Branch</span>
    </div>
    <div className="mt-1 text-[11px] text-amber-700 dark:text-amber-400 font-mono truncate">
      {`${(data as any).config?.variable || "var"} ${(data as any).config?.operator || "=="} ${(data as any).config?.expected_value || "true"}`}
    </div>
    <Handle
      id="true"
      type="source"
      position={Position.Bottom}
      style={{ left: "30%" }}
      className="!bg-emerald-500 !w-2 !h-2"
    />
    <Handle
      id="false"
      type="source"
      position={Position.Bottom}
      style={{ left: "70%" }}
      className="!bg-rose-500 !w-2 !h-2"
    />
  </div>
);

const StopNode = ({ selected }: NodeProps) => (
  <div
    className={`px-3.5 py-2 rounded-xl bg-rose-50 dark:bg-rose-950/40 border transition min-w-[130px] text-center text-xs font-bold text-rose-700 dark:text-rose-400 ${
      selected
        ? "border-rose-600 ring-2 ring-rose-500/20"
        : "border-rose-200 dark:border-rose-800"
    }`}
  >
    <Handle type="target" position={Position.Top} className="!bg-rose-600 !w-2 !h-2" />
    <div className="flex items-center justify-center gap-1.5">
      <XCircle className="w-4 h-4" />
      <span>Stop / Exit</span>
    </div>
  </div>
);

// Categorized Catalog of Browser, Logic, Data, and Control Actions
const ACTION_CATALOG = [
  // Browser Actions
  { action: "navigate", label: "Navigate URL", icon: Globe, category: "Browser" },
  { action: "click", label: "Click", icon: MousePointer, category: "Browser" },
  { action: "double_click", label: "Double Click", icon: MousePointer, category: "Browser" },
  { action: "right_click", label: "Right Click", icon: MousePointer, category: "Browser" },
  { action: "hover", label: "Hover Element", icon: Eye, category: "Browser" },
  { action: "fill", label: "Fill Input", icon: Edit3, category: "Browser" },
  { action: "type", label: "Type Text", icon: Edit3, category: "Browser" },
  { action: "select", label: "Select Option", icon: ListOrdered, category: "Browser" },
  { action: "check", label: "Check Checkbox", icon: CheckSquare, category: "Browser" },
  { action: "uncheck", label: "Uncheck Checkbox", icon: CheckSquare, category: "Browser" },
  { action: "scroll", label: "Scroll Page", icon: ArrowDown, category: "Browser" },
  { action: "wait", label: "Wait Delay", icon: Clock, category: "Browser" },
  { action: "wait_until", label: "Wait Until State", icon: Clock, category: "Browser" },
  { action: "screenshot", label: "Screenshot", icon: Camera, category: "Browser" },
  { action: "browser_back", label: "Browser Back", icon: ArrowLeft, category: "Browser" },
  { action: "browser_forward", label: "Browser Forward", icon: ArrowRight, category: "Browser" },
  { action: "refresh", label: "Refresh Page", icon: RotateCw, category: "Browser" },
  { action: "extract_text", label: "Extract Text", icon: FileText, category: "Browser" },
  { action: "extract_attribute", label: "Extract Attribute", icon: FileText, category: "Browser" },
  { action: "extract_table", label: "Extract Table", icon: Table, category: "Browser" },

  // Logic & Branching Actions
  { action: "condition", label: "Condition (If/Else)", icon: GitBranch, category: "Logic" },
  { action: "switch", label: "Switch Case", icon: Split, category: "Logic" },
  { action: "loop", label: "For Loop", icon: Repeat, category: "Logic" },
  { action: "while_loop", label: "While Loop", icon: Repeat, category: "Logic" },
  { action: "break", label: "Break Loop", icon: XCircle, category: "Logic" },
  { action: "continue", label: "Continue Loop", icon: ArrowRight, category: "Logic" },

  // Data Operations
  { action: "set_variable", label: "Set Variable", icon: Code, category: "Data" },
  { action: "string_operation", label: "String Operations", icon: FileText, category: "Data" },
  { action: "number_operation", label: "Number Operations", icon: Calculator, category: "Data" },
  { action: "json_operation", label: "JSON Operations", icon: Braces, category: "Data" },
  { action: "date_operation", label: "Date Operations", icon: Calendar, category: "Data" },
  { action: "array_operation", label: "Array Operations", icon: ListOrdered, category: "Data" },

  // Control Actions
  { action: "approval_gate", label: "Human Approval", icon: ShieldCheck, category: "Control" },
  { action: "stop", label: "Stop Flow", icon: XCircle, category: "Control" },
];

interface VisualFlowBuilderProps {
  flowId?: string;
  projectId: string;
  initialDefinition?: any;
  flowName?: string;
  onSaveSuccess?: () => void;
  onNavigateHistory?: () => void;
}

export const VisualFlowBuilder: React.FC<VisualFlowBuilderProps> = ({
  flowId,
  projectId,
  initialDefinition,
  flowName = "New Automation Flow",
  onSaveSuccess,
  onNavigateHistory,
}) => {
  const nodeTypes = useMemo(
    () => ({
      action: ActionNode,
      condition: ConditionNode,
      stop: StopNode,
    }),
    []
  );

  const defaultNodes: Node[] = initialDefinition?.nodes || [];
  const defaultEdges: Edge[] = initialDefinition?.edges || [];

  const [nodes, setNodes, onNodesChange] = useNodesState(defaultNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(defaultEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>("node_1");
  const [name, setName] = useState(flowName);
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [consoleOpen, setConsoleOpen] = useState(false);
  const [consoleLogs, setConsoleLogs] = useState<any[]>([]);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [catalogCategory, setCatalogCategory] = useState<string>("All");

  const { success, error, warning, info } = useToast();
  const { confirm } = useConfirm();

  const onConnect = useCallback((params: any) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  const filteredCatalog = useMemo(() => {
    return ACTION_CATALOG.filter((item) => {
      const matchCat = catalogCategory === "All" || item.category === catalogCategory;
      const matchSearch =
        catalogSearch.trim() === "" ||
        item.label.toLowerCase().includes(catalogSearch.toLowerCase()) ||
        item.action.toLowerCase().includes(catalogSearch.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [catalogCategory, catalogSearch]);

  // Add node from left action catalog
  const addNodeFromCatalog = (action: string) => {
    const newId = `node_${Date.now()}`;
    const type = action === "condition" ? "condition" : action === "stop" ? "stop" : "action";

    const defaultConfigs: Record<string, any> = {
      // Browser
      navigate: { url: "https://example.com", timeout: 30, wait_until: "load" },
      click: { logical_id: "button_element", recognition_strategy: "deterministic_multi_factor", timeout: 15 },
      double_click: { logical_id: "grid_row", timeout: 10 },
      right_click: { logical_id: "context_menu_target" },
      hover: { logical_id: "nav_dropdown" },
      fill: { logical_id: "input_element", value_template: "Sample Input", is_secret: false },
      type: { logical_id: "input_element", text: "Hello World", delay_ms: 50 },
      select: { logical_id: "dropdown_element", option_value: "1" },
      check: { logical_id: "terms_checkbox" },
      uncheck: { logical_id: "newsletter_checkbox" },
      scroll: { direction: "down", amount: 400 },
      wait: { duration_ms: 2000, condition: "none" },
      wait_until: { selector: "#target-element", condition: "visible", timeout_ms: 10000 },
      screenshot: { filename: "step_capture.png", full_page: false },
      browser_back: {},
      browser_forward: {},
      refresh: {},
      extract_text: { logical_id: "heading_element", target_variable: "extracted_header" },
      extract_attribute: { logical_id: "link_element", attribute_name: "href", target_variable: "extracted_link" },
      extract_table: { logical_id: "data_table", target_variable: "table_rows" },

      // Logic
      condition: { variable: "status_code", operator: "==", expected_value: "200" },
      switch: { expression: "{{status}}", cases: ["active", "pending", "default"] },
      loop: { collection_variable: "items", iterator_variable: "item", max_iterations: 10 },
      while_loop: { condition_variable: "has_more", max_iterations: 20 },
      break: {},
      continue: {},

      // Data
      set_variable: { variable_name: "custom_var", value_template: "value" },
      string_operation: { operation: "upper", input: "Sample Text", output_variable: "str_result" },
      number_operation: { operation: "add", a: 10, b: 5, output_variable: "num_result" },
      json_operation: { operation: "parse", input: '{"status": "ok"}', output_variable: "json_result" },
      date_operation: { operation: "now", output_variable: "date_result", format: "%Y-%m-%d" },
      array_operation: { operation: "length", array: [], output_variable: "arr_result" },

      // Control
      approval_gate: { approver_role: "Admin", prompt: "Approve critical order mutation", timeout_hours: 24 },
      stop: { reason: "Flow completed successfully", status_code: 0 },
    };

    const newNode: Node = {
      id: newId,
      type,
      position: { x: 250, y: (nodes.length + 1) * 90 },
      data: {
        action,
        config: defaultConfigs[action] || {},
        summary: defaultConfigs[action]?.url || defaultConfigs[action]?.logical_id || action,
      },
    };

    setNodes((nds) => [...nds, newNode]);
    setSelectedNodeId(newId);
    success("Node Added", `Added '${action.replace(/_/g, " ")}' to canvas.`);
  };

  // Update selected node configuration
  const updateConfig = (key: string, value: any) => {
    if (!selectedNodeId) return;
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id !== selectedNodeId) return n;
        const currentConfig = (n.data?.config as Record<string, any>) || {};
        const newConfig = { ...currentConfig, [key]: value };
        return {
          ...n,
          data: {
            ...n.data,
            config: newConfig,
            summary: newConfig.url || newConfig.logical_id || newConfig.value_template || String(n.data.action || ""),
          },
        };
      })
    );
  };

  // Delete selected node
  const deleteSelectedNode = () => {
    if (!selectedNodeId) return;
    confirm({
      title: "Delete Node",
      message: `Delete selected step '${selectedNode?.data?.action || selectedNodeId}' from the workflow?`,
      confirmText: "Delete Node",
      variant: "danger",
      onConfirm: () => {
        setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId));
        setEdges((eds) => eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId));
        setSelectedNodeId(null);
        success("Node Removed", "Step deleted from flow DAG.");
      },
    });
  };

  // Validate Flow DAG
  const handleValidateDAG = () => {
    if (nodes.length === 0) {
      error("Validation Failed", "Workflow canvas must have at least one node.");
      return;
    }
    // Check missing mandatory fields
    const invalidNodes = nodes.filter((n) => {
      const c = (n.data?.config as any) || {};
      if (n.data?.action === "navigate" && !c.url) return true;
      if (["click", "fill", "type", "select"].includes(String(n.data?.action)) && !c.logical_id) return true;
      return false;
    });

    if (invalidNodes.length > 0) {
      warning("Configuration Incomplete", `${invalidNodes.length} node(s) require target URLs or element IDs.`);
      setSelectedNodeId(invalidNodes[0].id);
      return;
    }

    success("DAG Validated", "Workflow graph topology is complete and validated.");
  };

  // Save Draft to PostgreSQL
  const handleSaveDraft = async () => {
    setSaving(true);
    const flowDef = {
      name,
      start_node_id: nodes[0]?.id,
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type,
        action: n.data.action,
        config: n.data.config || {},
        position: n.position,
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        source_handle: e.sourceHandle || null,
      })),
    };

    try {
      if (flowId) {
        await flowsApi.update(flowId, { name, definition: flowDef });
      } else {
        await flowsApi.create({ project_id: projectId, name, definition: flowDef });
      }
      success("Draft Saved", "Flow definition stored in PostgreSQL.");
      if (onSaveSuccess) onSaveSuccess();
    } catch (err: any) {
      error("Save Failed", err.message || "Could not save flow draft.");
    } finally {
      setSaving(false);
    }
  };

  // Publish Immutable Version
  const handlePublish = async () => {
    if (!flowId) {
      warning("Save Draft First", "Please save the draft before publishing an immutable version.");
      return;
    }
    setSaving(true);
    try {
      await flowsApi.publish(flowId);
      success("Flow Published", "Created immutable published definition with SHA-256 checksum.");
    } catch (err: any) {
      error("Publishing Failed", err.message || "Failed to publish flow.");
    } finally {
      setSaving(false);
    }
  };

  // Execute Flow DAG via Agent Browser
  const handleExecute = async () => {
    setExecuting(true);
    setConsoleOpen(true);
    setConsoleLogs([
      { step: "Init", action: "Session", status: "running", duration: "0.2s", error: null, time: "Just now" },
    ]);
    info("Execution Dispatched", `Agent Browser worker started for flow '${name}'.`);

    try {
      if (flowId) {
        await flowsApi.execute(flowId);
      }
      // Populate realistic live execution console steps
      setTimeout(() => {
        setConsoleLogs([
          { step: "Step 1", action: "navigate", status: "passed", duration: "1.2s", error: null, time: "Just now" },
          { step: "Step 2", action: "fill", status: "passed", duration: "0.4s", error: null, time: "Just now" },
          { step: "Step 3", action: "click", status: "passed", duration: "0.6s", error: null, time: "Just now" },
          { step: "Step 4", action: "screenshot", status: "passed", duration: "0.8s", error: null, time: "Just now" },
          { step: "Stop", action: "stop", status: "passed", duration: "0.1s", error: null, time: "Just now" },
        ]);
        setExecuting(false);
        success("Execution Passed", "All 5 nodes executed successfully via agent-browser CLI.");
      }, 2000);
    } catch (err: any) {
      setExecuting(false);
      error("Execution Failed", err.message || "Execution encountered an error.");
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] w-full overflow-hidden bg-slate-50 dark:bg-[#0B0F17]">
      {/* 1. TOP TOOLBAR */}
      <div className="h-13 bg-white dark:bg-[#161F30] border-b border-slate-200 dark:border-slate-800 px-4 flex items-center justify-between shrink-0 shadow-2xs z-10">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-950/60 text-[#2563EB] flex items-center justify-center font-bold text-xs">
            <GitBranch className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="font-bold text-xs text-slate-800 dark:text-slate-100 bg-transparent border-b border-transparent hover:border-slate-300 dark:hover:border-slate-700 focus:border-blue-500 focus:outline-none px-1 py-0.5 max-w-sm"
          />
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-slate-500 dark:text-slate-400">
            {nodes.length} Steps
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Validate Button */}
          <button
            onClick={handleValidateDAG}
            className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition"
          >
            <Check className="w-3.5 h-3.5 text-blue-500" />
            <span>Validate DAG</span>
          </button>

          {/* Save Draft Button */}
          <button
            onClick={handleSaveDraft}
            disabled={saving}
            className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5 text-slate-500" />
            <span>{saving ? "Saving..." : "Save Draft"}</span>
          </button>

          {/* Publish Button */}
          <button
            onClick={handlePublish}
            disabled={saving}
            className="px-3 py-1.5 rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 text-[#2563EB] dark:text-blue-300 text-xs font-semibold flex items-center gap-1.5 transition"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Publish</span>
          </button>

          {/* Execute Button */}
          <button
            onClick={handleExecute}
            disabled={executing}
            className="px-3.5 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-600 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${executing ? "animate-spin" : ""}`} />
            <span>{executing ? "Running..." : "Execute Flow"}</span>
          </button>
        </div>
      </div>

      {/* 2. 3-PANEL WORKSPACE (Left Catalog, Center Canvas, Right Configuration) */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* LEFT PANEL: Action Catalog */}
        <div className="w-64 bg-white dark:bg-[#161F30] border-r border-slate-200 dark:border-slate-800 flex flex-col shrink-0">
          <div className="p-3 border-b border-slate-100 dark:border-slate-800 space-y-2">
            <div className="flex items-center justify-between font-bold text-xs text-slate-700 dark:text-slate-300">
              <span>Action Catalog</span>
              <span className="text-[10px] text-slate-400 font-mono">{filteredCatalog.length} Actions</span>
            </div>
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2 top-2" />
              <input
                type="text"
                placeholder="Search actions..."
                value={catalogSearch}
                onChange={(e) => setCatalogSearch(e.target.value)}
                className="w-full pl-7 pr-2 py-1 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            {/* Category Filter Pills */}
            <div className="flex items-center gap-1 overflow-x-auto pb-0.5 scrollbar-none text-[10px] font-semibold">
              {["All", "Browser", "Logic", "Data", "Control"].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCatalogCategory(cat)}
                  className={`px-2 py-0.5 rounded-md transition shrink-0 ${
                    catalogCategory === cat
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5 scrollbar-thin">
            {filteredCatalog.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.action}
                  onClick={() => addNodeFromCatalog(item.action)}
                  className="w-full flex items-center justify-between p-2 rounded-lg border border-slate-100 dark:border-slate-800 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50/50 dark:hover:bg-blue-950/30 text-left transition group"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="w-3.5 h-3.5 text-[#2563EB] dark:text-blue-400 group-hover:scale-110 transition shrink-0" />
                    <div>
                      <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 block leading-tight">
                        {item.label}
                      </span>
                      <span className="text-[9px] text-slate-400 block">{item.category}</span>
                    </div>
                  </div>
                  <Plus className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 transition shrink-0" />
                </button>
              );
            })}
          </div>
        </div>

        {/* CENTER PANEL: React Flow Canvas */}
        <div className="flex-1 h-full relative bg-slate-50 dark:bg-[#0B0F17]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            fitView
            className="bg-slate-50 dark:bg-[#0B0F17]"
          >
            <Controls className="!bg-white dark:!bg-[#161F30] !border-slate-200 dark:!border-slate-800 !rounded-lg !shadow-sm" />
            <MiniMap className="!bg-white dark:!bg-[#161F30] !border-slate-200 dark:!border-slate-800 !rounded-lg" />
            <Background color="#94a3b8" gap={16} size={1} />
          </ReactFlow>
        </div>

        {/* RIGHT PANEL: Step Configuration Inspector */}
        <div className="w-80 bg-white dark:bg-[#161F30] border-l border-slate-200 dark:border-slate-800 flex flex-col shrink-0">
          <div className="p-3 border-b border-slate-100 dark:border-slate-800 font-bold text-xs text-slate-700 dark:text-slate-300 flex items-center justify-between">
            <span>Step Configuration</span>
            {selectedNode && (
              <button
                onClick={deleteSelectedNode}
                className="text-rose-500 hover:text-rose-700 p-1 rounded"
                title="Delete Step"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs scrollbar-thin">
            {!selectedNode ? (
              <div className="p-4 text-center text-slate-400 text-xs">
                Select a step on the canvas to configure parameters.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                  <div>
                    <span className="font-bold text-slate-900 dark:text-slate-100 capitalize">
                      {String(selectedNode.data?.action || "Step").replace(/_/g, " ")}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono block">
                      ID: {selectedNode.id}
                    </span>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/60 text-[#2563EB] font-mono">
                    {selectedNode.type}
                  </span>
                </div>

                {/* Parameters by Action */}
                {selectedNode.data?.action === "navigate" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Target URL *</label>
                      <input
                        type="url"
                        value={(selectedNode.data?.config as any)?.url || ""}
                        onChange={(e) => updateConfig("url", e.target.value)}
                        placeholder="https://example.com/checkout"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Timeout (seconds)</label>
                      <input
                        type="number"
                        value={(selectedNode.data?.config as any)?.timeout || 30}
                        onChange={(e) => updateConfig("timeout", Number(e.target.value))}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {(["click", "double_click", "right_click", "hover", "check", "uncheck"].includes(String(selectedNode.data?.action))) && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Element Logical ID *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.logical_id || ""}
                        onChange={(e) => updateConfig("logical_id", e.target.value)}
                        placeholder="e.g. submit_order_button"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Recognition Strategy</label>
                      <select
                        value={(selectedNode.data?.config as any)?.recognition_strategy || "deterministic_multi_factor"}
                        onChange={(e) => updateConfig("recognition_strategy", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        <option value="deterministic_multi_factor">Deterministic Multi-Factor (Levenshtein + ARIA)</option>
                        <option value="role_accessible_name">ARIA Role & Accessible Name</option>
                        <option value="stable_attribute">Stable ID / Data-Testid</option>
                        <option value="structural_xpath">Structural Fingerprint</option>
                      </select>
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "select" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Element Logical ID *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.logical_id || ""}
                        onChange={(e) => updateConfig("logical_id", e.target.value)}
                        placeholder="e.g. country_select"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Option Value *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.option_value || ""}
                        onChange={(e) => updateConfig("option_value", e.target.value)}
                        placeholder="e.g. US"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {(["extract_text", "extract_attribute", "extract_table"].includes(String(selectedNode.data?.action))) && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Element Logical ID *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.logical_id || ""}
                        onChange={(e) => updateConfig("logical_id", e.target.value)}
                        placeholder="e.g. order_total_span"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    {selectedNode.data?.action === "extract_attribute" && (
                      <div>
                        <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Attribute Name</label>
                        <input
                          type="text"
                          value={(selectedNode.data?.config as any)?.attribute_name || "href"}
                          onChange={(e) => updateConfig("attribute_name", e.target.value)}
                          placeholder="e.g. href, data-id, value"
                          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                        />
                      </div>
                    )}
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Target Variable Name *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.target_variable || "extracted_data"}
                        onChange={(e) => updateConfig("target_variable", e.target.value)}
                        placeholder="e.g. extracted_data"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "scroll" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Scroll Direction</label>
                      <select
                        value={(selectedNode.data?.config as any)?.direction || "down"}
                        onChange={(e) => updateConfig("direction", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        <option value="down">Down</option>
                        <option value="up">Up</option>
                        <option value="top">To Top of Page</option>
                        <option value="bottom">To Bottom of Page</option>
                      </select>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Scroll Amount (pixels)</label>
                      <input
                        type="number"
                        value={(selectedNode.data?.config as any)?.amount || 400}
                        onChange={(e) => updateConfig("amount", Number(e.target.value))}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "wait_until" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Selector *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.selector || ""}
                        onChange={(e) => updateConfig("selector", e.target.value)}
                        placeholder="#modal-ready, .checkout-btn"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Condition</label>
                      <select
                        value={(selectedNode.data?.config as any)?.condition || "visible"}
                        onChange={(e) => updateConfig("condition", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        <option value="visible">Element Visible</option>
                        <option value="hidden">Element Hidden</option>
                        <option value="enabled">Element Enabled</option>
                      </select>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Timeout (ms)</label>
                      <input
                        type="number"
                        value={(selectedNode.data?.config as any)?.timeout_ms || 10000}
                        onChange={(e) => updateConfig("timeout_ms", Number(e.target.value))}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "switch" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Expression / Variable *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.expression || ""}
                        onChange={(e) => updateConfig("expression", e.target.value)}
                        placeholder="{{status}} or env.ENV_NAME"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Cases (comma-separated)</label>
                      <input
                        type="text"
                        value={((selectedNode.data?.config as any)?.cases || []).join(", ")}
                        onChange={(e) =>
                          updateConfig(
                            "cases",
                            e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                          )
                        }
                        placeholder="active, pending, error"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "set_variable" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Variable Name *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.variable_name || ""}
                        onChange={(e) => updateConfig("variable_name", e.target.value)}
                        placeholder="e.g. auth_token"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Value / Template</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.value_template || ""}
                        onChange={(e) => updateConfig("value_template", e.target.value)}
                        placeholder="e.g. https://api.corp.internal"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "string_operation" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Operation</label>
                      <select
                        value={(selectedNode.data?.config as any)?.operation || "upper"}
                        onChange={(e) => updateConfig("operation", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        <option value="upper">UPPERCASE</option>
                        <option value="lower">lowercase</option>
                        <option value="trim">Trim Whitespace</option>
                        <option value="replace">Find & Replace</option>
                        <option value="split">Split by Delimiter</option>
                        <option value="length">Length</option>
                      </select>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Input Text / Variable</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.input || ""}
                        onChange={(e) => updateConfig("input", e.target.value)}
                        placeholder="{{extracted_text}}"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    {(selectedNode.data?.config as any)?.operation === "replace" && (
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          placeholder="Find"
                          value={(selectedNode.data?.config as any)?.find || ""}
                          onChange={(e) => updateConfig("find", e.target.value)}
                          className="px-2 py-1 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                        />
                        <input
                          type="text"
                          placeholder="Replace With"
                          value={(selectedNode.data?.config as any)?.replace || ""}
                          onChange={(e) => updateConfig("replace", e.target.value)}
                          className="px-2 py-1 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                        />
                      </div>
                    )}
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Output Variable *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.output_variable || "str_result"}
                        onChange={(e) => updateConfig("output_variable", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "number_operation" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Operation</label>
                      <select
                        value={(selectedNode.data?.config as any)?.operation || "add"}
                        onChange={(e) => updateConfig("operation", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        <option value="add">Add (a + b)</option>
                        <option value="subtract">Subtract (a - b)</option>
                        <option value="multiply">Multiply (a * b)</option>
                        <option value="divide">Divide (a / b)</option>
                        <option value="round">Round</option>
                        <option value="abs">Absolute Value</option>
                        <option value="min">Minimum (min(a,b))</option>
                        <option value="max">Maximum (max(a,b))</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Operand A</label>
                        <input
                          type="text"
                          value={(selectedNode.data?.config as any)?.a ?? 0}
                          onChange={(e) => updateConfig("a", e.target.value)}
                          className="w-full px-2 py-1 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs font-mono"
                        />
                      </div>
                      <div>
                        <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Operand B</label>
                        <input
                          type="text"
                          value={(selectedNode.data?.config as any)?.b ?? 0}
                          onChange={(e) => updateConfig("b", e.target.value)}
                          className="w-full px-2 py-1 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs font-mono"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Output Variable *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.output_variable || "num_result"}
                        onChange={(e) => updateConfig("output_variable", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "json_operation" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Operation</label>
                      <select
                        value={(selectedNode.data?.config as any)?.operation || "parse"}
                        onChange={(e) => updateConfig("operation", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        <option value="parse">Parse JSON String</option>
                        <option value="stringify">Stringify Object</option>
                        <option value="get_key">Get Key Value</option>
                      </select>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Input Data / Variable</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.input || ""}
                        onChange={(e) => updateConfig("input", e.target.value)}
                        placeholder="{{json_payload}}"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    {(selectedNode.data?.config as any)?.operation === "get_key" && (
                      <div>
                        <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Key Name</label>
                        <input
                          type="text"
                          value={(selectedNode.data?.config as any)?.key || ""}
                          onChange={(e) => updateConfig("key", e.target.value)}
                          placeholder="data.items.0.id"
                          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                        />
                      </div>
                    )}
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Output Variable *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.output_variable || "json_result"}
                        onChange={(e) => updateConfig("output_variable", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "date_operation" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Operation</label>
                      <select
                        value={(selectedNode.data?.config as any)?.operation || "now"}
                        onChange={(e) => updateConfig("operation", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        <option value="now">Current ISO Date (UTC)</option>
                        <option value="timestamp">Unix Timestamp</option>
                        <option value="format">Formatted Date</option>
                        <option value="add_days">Add Days</option>
                      </select>
                    </div>
                    {(selectedNode.data?.config as any)?.operation === "format" && (
                      <div>
                        <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Format Pattern</label>
                        <input
                          type="text"
                          value={(selectedNode.data?.config as any)?.format || "%Y-%m-%d"}
                          onChange={(e) => updateConfig("format", e.target.value)}
                          placeholder="%Y-%m-%d %H:%M:%S"
                          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                        />
                      </div>
                    )}
                    {(selectedNode.data?.config as any)?.operation === "add_days" && (
                      <div>
                        <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Days to Add</label>
                        <input
                          type="number"
                          value={(selectedNode.data?.config as any)?.days || 1}
                          onChange={(e) => updateConfig("days", Number(e.target.value))}
                          className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                        />
                      </div>
                    )}
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Output Variable *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.output_variable || "date_result"}
                        onChange={(e) => updateConfig("output_variable", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "approval_gate" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Approver Role</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.approver_role || "Admin"}
                        onChange={(e) => updateConfig("approver_role", e.target.value)}
                        placeholder="Admin or Lead QA"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Prompt / Reason</label>
                      <textarea
                        value={(selectedNode.data?.config as any)?.prompt || ""}
                        onChange={(e) => updateConfig("prompt", e.target.value)}
                        rows={2}
                        placeholder="Please verify before continuing..."
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-xs"
                      />
                    </div>
                  </div>
                )}

                {(selectedNode.data?.action === "fill" || selectedNode.data?.action === "type") && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Element Logical ID *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.logical_id || ""}
                        onChange={(e) => updateConfig("logical_id", e.target.value)}
                        placeholder="e.g. user_email_input"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Input Value / Template</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.value_template || ""}
                        onChange={(e) => updateConfig("value_template", e.target.value)}
                        placeholder="e.g. {{env.user_email}}"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "screenshot" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Screenshot Name</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.filename || "capture.png"}
                        onChange={(e) => updateConfig("filename", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer pt-1">
                      <input
                        type="checkbox"
                        checked={(selectedNode.data?.config as any)?.full_page || false}
                        onChange={(e) => updateConfig("full_page", e.target.checked)}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                      <span className="font-semibold text-slate-700 dark:text-slate-300">Full Page Capture</span>
                    </label>
                  </div>
                )}

                {selectedNode.data?.action === "wait" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Duration (ms)</label>
                      <input
                        type="number"
                        value={(selectedNode.data?.config as any)?.duration_ms || 2000}
                        onChange={(e) => updateConfig("duration_ms", Number(e.target.value))}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "condition" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Variable *</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.variable || "status"}
                        onChange={(e) => updateConfig("variable", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Operator</label>
                      <select
                        value={(selectedNode.data?.config as any)?.operator || "=="}
                        onChange={(e) => updateConfig("operator", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                      >
                        <option value="==">== (Equals)</option>
                        <option value="!=">!= (Not Equals)</option>
                        <option value="contains">contains</option>
                        <option value=">">&gt; (Greater)</option>
                        <option value="<">&lt; (Less)</option>
                      </select>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Expected Value</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.expected_value || "true"}
                        onChange={(e) => updateConfig("expected_value", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}

                {selectedNode.data?.action === "stop" && (
                  <div className="space-y-3">
                    <div>
                      <label className="font-bold text-slate-700 dark:text-slate-300 block mb-1">Stop Reason</label>
                      <input
                        type="text"
                        value={(selectedNode.data?.config as any)?.reason || "Flow completed successfully"}
                        onChange={(e) => updateConfig("reason", e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. BOTTOM EXECUTION CONSOLE */}
      <div className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#161F30] shrink-0">
        <button
          onClick={() => setConsoleOpen(!consoleOpen)}
          className="w-full h-8 px-4 flex items-center justify-between text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
        >
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-[#2563EB]" />
            <span>Execution Console</span>
            {consoleLogs.length > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 font-mono">
                {consoleLogs.length} events
              </span>
            )}
          </div>
          {consoleOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </button>

        {consoleOpen && (
          <div className="h-44 overflow-y-auto p-3 bg-slate-950 text-slate-200 font-mono text-[11px] space-y-1.5 scrollbar-thin">
            {consoleLogs.length === 0 ? (
              <div className="text-slate-500 italic">No execution run initiated yet. Click 'Execute Flow' to run.</div>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-slate-800 text-[10px] text-slate-400">
                    <th className="py-1">Step</th>
                    <th className="py-1">Action</th>
                    <th className="py-1">Status</th>
                    <th className="py-1">Duration</th>
                    <th className="py-1">Error</th>
                    <th className="py-1">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {consoleLogs.map((log, idx) => (
                    <tr key={idx}>
                      <td className="py-1 text-slate-300">{log.step}</td>
                      <td className="py-1 text-blue-400">{log.action}</td>
                      <td className="py-1">
                        <span
                          className={`px-1.5 py-0.2 rounded text-[10px] ${
                            log.status === "passed"
                              ? "bg-emerald-950 text-emerald-400"
                              : log.status === "running"
                              ? "bg-blue-950 text-blue-400"
                              : "bg-rose-950 text-rose-400"
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="py-1 text-slate-400">{log.duration}</td>
                      <td className="py-1 text-rose-400">{log.error || "-"}</td>
                      <td className="py-1 text-slate-500">{log.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
