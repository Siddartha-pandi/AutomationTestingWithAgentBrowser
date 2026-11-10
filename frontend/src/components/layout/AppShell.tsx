"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  LayoutDashboard,
  GitBranch,
  PlusCircle,
  Calendar,
  CheckSquare,
  FolderKanban,
  Wrench,
  FileText,
  Compass,
  Code2,
  Crosshair,
  Sparkles,
  History,
  PlayCircle,
  Clock,
  Terminal,
  Image as ImageIcon,
  Layers,
  Globe,
  KeyRound,
  Sliders,
  Users,
  ShieldAlert,
  ShieldCheck,
  ClipboardList,
  LogOut,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Building2,
  Lock,
  Search,
  Bell,
  Sun,
  Moon,
  User,
  Check,
  X,
  ExternalLink,
  Cpu,
  Activity,
  FileCode,
} from "lucide-react";
import { useTheme } from "../common/ThemeProvider";
import { BrowserAutomationLogo } from "../common/BrowserLogo";

export type NavView =
  | "dashboard_overview"
  | "automation_all_flows"
  | "automation_builder"
  | "automation_create_flow"
  | "automation_schedules"
  | "testing_cases"
  | "testing_suites"
  | "testing_builder"
  | "testing_reports"
  | "browser_live"
  | "browser_dom"
  | "browser_profiles"
  | "browser_recognition"
  | "browser_healing"
  | "executions_running"
  | "executions_history"
  | "executions_details"
  | "executions_logs"
  | "executions_screenshots"
  | "config_projects"
  | "config_environments"
  | "config_credentials"
  | "config_browser"
  | "admin_users"
  | "admin_roles"
  | "admin_audit"
  | "user_profile";

interface NavItem {
  id: NavView;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    title: "DASHBOARD",
    items: [
      { id: "dashboard_overview", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
  {
    title: "AUTOMATION",
    items: [
      { id: "automation_all_flows", label: "All Flows", icon: GitBranch },
      { id: "automation_builder", label: "Flow Builder", icon: Wrench },
      { id: "automation_create_flow", label: "Create Flow", icon: PlusCircle },
      { id: "automation_schedules", label: "Schedules", icon: Calendar },
    ],
  },
  {
    title: "TESTING",
    items: [
      { id: "testing_cases", label: "Test Cases", icon: CheckSquare },
      { id: "testing_suites", label: "Test Suites", icon: FolderKanban },
      { id: "testing_builder", label: "Test Builder", icon: FileCode },
      { id: "testing_reports", label: "Test Reports", icon: FileText },
    ],
  },
  {
    title: "BROWSER INTELLIGENCE",
    items: [
      { id: "browser_live", label: "Live Browser", icon: Compass },
      { id: "browser_dom", label: "DOM Explorer", icon: Code2 },
      { id: "browser_profiles", label: "Element Profiles", icon: Crosshair },
      { id: "browser_recognition", label: "Element Recognition", icon: Sparkles },
      { id: "browser_healing", label: "Self-Healing History", icon: History },
    ],
  },
  {
    title: "EXECUTIONS",
    items: [
      { id: "executions_running", label: "Running Executions", icon: PlayCircle, badge: "Live" },
      { id: "executions_history", label: "Execution History", icon: Clock },
      { id: "executions_details", label: "Execution Details", icon: Activity },
      { id: "executions_logs", label: "Logs", icon: Terminal },
      { id: "executions_screenshots", label: "Screenshots", icon: ImageIcon },
    ],
  },
  {
    title: "CONFIGURATION",
    items: [
      { id: "config_projects", label: "Projects", icon: Layers },
      { id: "config_environments", label: "Environments", icon: Globe },
      { id: "config_credentials", label: "Credentials", icon: KeyRound },
      { id: "config_browser", label: "Browser Settings", icon: Sliders },
    ],
  },
  {
    title: "ADMINISTRATION",
    items: [
      { id: "admin_users", label: "Users", icon: Users },
      { id: "admin_roles", label: "Roles & Permissions", icon: ShieldAlert },
      { id: "admin_audit", label: "Audit Logs", icon: ClipboardList },
    ],
  },
];

interface Notification {
  id: string;
  title: string;
  description: string;
  time: string;
  read: boolean;
  type: "success" | "warning" | "info";
}

interface AppShellProps {
  currentView: NavView;
  onNavigate: (view: NavView) => void;
  user: { email: string; full_name?: string; role?: string } | null;
  onLogout: () => void;
  currentProject: { id: string; name: string } | null;
  children: React.ReactNode;
}

export function AppShell({
  currentView,
  onNavigate,
  user,
  onLogout,
  currentProject,
  children,
}: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  const { resolvedTheme, toggleTheme } = useTheme();

  const [notifications, setNotifications] = useState<Notification[]>([
    {
      id: "n1",
      title: "Self-Healing Triggered",
      description: "Element '#submit-order' healed with 96.4% confidence",
      time: "10m ago",
      read: false,
      type: "success",
    },
    {
      id: "n2",
      title: "Schedule Execution Complete",
      description: "Daily QA Regression Suite passed 28/28 assertions",
      time: "1h ago",
      read: false,
      type: "info",
    },
    {
      id: "n3",
      title: "Healing Approval Required",
      description: "Checkout button changed in Staging. Confidence 91.2%",
      time: "3h ago",
      read: true,
      type: "warning",
    },
  ]);

  const searchInputRef = useRef<HTMLInputElement>(null);

  // Shortcut Ctrl+K / Cmd+K for global search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setSearchOpen(false);
        setNotificationsOpen(false);
        setProfileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (searchOpen) {
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [searchOpen]);

  // Derive human-readable section breadcrumb
  let activeSectionTitle = "Dashboard";
  let activeItemLabel = "Dashboard";
  for (const sec of NAV_SECTIONS) {
    const item = sec.items.find((i) => i.id === currentView);
    if (item) {
      activeSectionTitle = sec.title;
      activeItemLabel = item.label;
      break;
    }
  }
  if (currentView === "user_profile") {
    activeSectionTitle = "SETTINGS";
    activeItemLabel = "User Profile & Preferences";
  }

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  // Filter search items across all 27 pages
  const allNavItems = NAV_SECTIONS.flatMap((s) =>
    s.items.map((i) => ({ ...i, section: s.title }))
  );
  if (allNavItems.every((i) => i.id !== "user_profile")) {
    allNavItems.push({
      id: "user_profile",
      label: "User Profile & Preferences",
      icon: User,
      section: "SETTINGS",
    });
  }

  const filteredSearchItems = searchQuery.trim()
    ? allNavItems.filter(
        (i) =>
          i.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          i.section.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : allNavItems;

  return (
    <div className="flex h-screen w-full bg-[#F8FAFC] dark:bg-[#0B0F17] text-[#0F172A] dark:text-[#F8FAFC] font-sans antialiased overflow-hidden">
      {/* 1. SIDEBAR (Dark Navy #111827) */}
      <aside
        className={`flex flex-col bg-[#111827] dark:bg-[#090D16] border-r border-[#1F2937] transition-all duration-200 z-30 ${
          collapsed ? "w-16" : "w-64"
        } shrink-0 select-none`}
      >
        {/* Brand / Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#1F2937]">
          {!collapsed ? (
            <div className="flex items-center gap-2.5 overflow-hidden">
              <BrowserAutomationLogo size={32} className="shrink-0" />
              <div className="leading-tight truncate">
                <div className="font-bold text-xs tracking-tight text-white truncate">
                  AgentBrowser
                </div>
                <div className="text-[10px] text-blue-400 font-medium tracking-wider uppercase truncate">
                  Automation & Testing
                </div>
              </div>
            </div>
          ) : (
            <BrowserAutomationLogo size={32} className="mx-auto" />
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition"
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Project Selector Indicator & Switcher */}
        {!collapsed && (
          <button
            type="button"
            onClick={() => onNavigate("config_projects")}
            title="Click to switch workspace"
            className="w-full text-left px-4 py-2.5 bg-[#161F30] hover:bg-[#1E293B] border-b border-[#1F2937] flex items-center justify-between text-xs transition cursor-pointer group"
          >
            <div className="flex items-center gap-2 text-slate-300 truncate">
              <Building2 className="w-3.5 h-3.5 text-blue-400 shrink-0 group-hover:text-blue-300" />
              <div className="flex flex-col truncate">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                  Workspace
                </span>
                <span className="font-bold text-slate-100 truncate text-xs">
                  {currentProject?.name || "Enterprise QA Suite"}
                </span>
              </div>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800 font-mono">
              Active
            </span>
          </button>
        )}

        {/* Navigation List across 7 Categories */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-3.5 text-xs scrollbar-thin">
          {NAV_SECTIONS.map((sec) => (
            <div key={sec.title} className="space-y-1">
              {!collapsed && (
                <div className="px-2 py-0.5 text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                  {sec.title}
                </div>
              )}
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.id)}
                    title={collapsed ? item.label : undefined}
                    className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg font-medium transition text-left relative ${
                      isActive
                        ? "bg-[#2563EB] text-white font-semibold shadow-xs"
                        : "text-slate-300 hover:text-white hover:bg-slate-800/80"
                    }`}
                  >
                    <Icon
                      className={`w-4 h-4 shrink-0 ${
                        isActive ? "text-white" : "text-slate-400 group-hover:text-white"
                      }`}
                    />
                    {!collapsed && (
                      <span className="truncate flex-1">{item.label}</span>
                    )}
                    {!collapsed && item.badge && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono font-medium">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Company Data Protection Guarantee Badge */}
        {!collapsed && (
          <div className="mx-3 my-2 p-2 rounded-lg border border-emerald-800/60 bg-emerald-950/40 text-[10px] text-emerald-300 space-y-0.5">
            <div className="flex items-center gap-1 font-bold text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Company Data Protection</span>
            </div>
            <div className="text-emerald-300/90 leading-tight">
              100% Deterministic Engine. Zero AI / No-LLMs.
            </div>
          </div>
        )}

        {/* User Info / Profile footer */}
        <div className="p-3 border-t border-[#1F2937] bg-[#111827] flex items-center justify-between gap-2">
          {!collapsed ? (
            <button
              onClick={() => onNavigate("user_profile")}
              className="flex items-center gap-2 overflow-hidden text-left hover:opacity-90 transition flex-1"
            >
              <div className="w-7 h-7 rounded-full bg-[#2563EB] text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-xs">
                {user?.full_name ? user.full_name[0].toUpperCase() : user?.email ? user.email[0].toUpperCase() : "U"}
              </div>
              <div className="overflow-hidden leading-tight flex-1">
                <div className="font-semibold text-slate-100 truncate text-xs">
                  {user?.full_name || user?.email?.split("@")[0] || "Administrator"}
                </div>
                <div className="text-[10px] text-slate-400 truncate capitalize">
                  {user?.role || "Owner"}
                </div>
              </div>
            </button>
          ) : (
            <button
              onClick={() => onNavigate("user_profile")}
              className="w-7 h-7 mx-auto rounded-full bg-[#2563EB] text-white flex items-center justify-center font-bold text-xs"
              title="Profile"
            >
              {user?.email ? user.email[0].toUpperCase() : "U"}
            </button>
          )}
          {!collapsed && (
            <button
              onClick={onLogout}
              title="Sign out"
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </aside>

      {/* 2. MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* TOP HEADER */}
        <header className="h-14 bg-white dark:bg-[#111827] border-b border-[#E2E8F0] dark:border-[#1F2937] px-6 flex items-center justify-between shrink-0 shadow-xs z-20">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center gap-2 text-xs">
            <span className="font-semibold text-slate-400 dark:text-slate-400 uppercase tracking-wider text-[11px]">
              {activeSectionTitle}
            </span>
            <span className="text-slate-300 dark:text-slate-600">/</span>
            <span className="font-bold text-[#2563EB] dark:text-blue-400 text-xs">
              {activeItemLabel}
            </span>
          </div>

          {/* Center/Right Action Controls */}
          <div className="flex items-center gap-3">
            {/* Global Search Input Button */}
            <button
              onClick={() => setSearchOpen(true)}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-300 text-xs transition shadow-2xs w-60 justify-between"
            >
              <div className="flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[11px]">Global search...</span>
              </div>
              <kbd className="px-1.5 py-0.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[10px] font-mono text-slate-400">
                Ctrl K
              </kbd>
            </button>

            {/* Deterministic Agent Browser status pill */}
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-[11px] font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>agent-browser v0.41.2</span>
              <span className="text-slate-400 dark:text-slate-500">•</span>
              <span className="text-emerald-700 dark:text-emerald-400 font-sans font-medium text-[10px]">
                Deterministic DOM
              </span>
            </div>

            {/* Quick action buttons */}
            <button
              onClick={() => onNavigate("automation_create_flow")}
              className="px-3 py-1.5 rounded-lg bg-[#2563EB] hover:bg-blue-700 text-white font-semibold text-xs flex items-center gap-1.5 shadow-xs transition"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Create Flow</span>
            </button>

            {/* Light / Dark Mode Toggle */}
            <button
              onClick={toggleTheme}
              title={resolvedTheme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
            >
              {resolvedTheme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
            </button>

            {/* Notification Drawer Toggle */}
            <div className="relative">
              <button
                onClick={() => {
                  setNotificationsOpen(!notificationsOpen);
                  setProfileMenuOpen(false);
                }}
                className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition relative"
                title="Notifications"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#EF4444] text-white text-[9px] font-bold flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Popover Dropdown */}
              {notificationsOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl p-3 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-slate-800 dark:text-slate-100">Notifications</span>
                      {unreadCount > 0 && (
                        <span className="px-1.5 py-0.2 bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 text-[10px] rounded font-semibold">
                          {unreadCount} new
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        onClick={markAllRead}
                        className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline font-medium"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>

                  <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-72 overflow-y-auto mt-1 scrollbar-thin">
                    {notifications.map((n) => (
                      <div
                        key={n.id}
                        className={`py-2 px-1 text-xs transition ${
                          !n.read ? "bg-blue-50/50 dark:bg-blue-950/20" : ""
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-800 dark:text-slate-200 text-xs">
                            {n.title}
                          </span>
                          <span className="text-[10px] text-slate-400">{n.time}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                          {n.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* User Profile Avatar Dropdown */}
            <div className="relative">
              <button
                onClick={() => {
                  setProfileMenuOpen(!profileMenuOpen);
                  setNotificationsOpen(false);
                }}
                className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
              >
                <div className="w-7 h-7 rounded-full bg-[#2563EB] text-white flex items-center justify-center font-bold text-xs">
                  {user?.full_name ? user.full_name[0].toUpperCase() : user?.email ? user.email[0].toUpperCase() : "A"}
                </div>
                <div className="hidden sm:block text-left text-xs leading-tight">
                  <div className="font-bold text-slate-800 dark:text-slate-100 truncate max-w-[100px]">
                    {user?.full_name?.split(" ")[0] || "Admin"}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 capitalize">
                    {user?.role || "Owner"}
                  </div>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {/* Profile Menu Popover */}
              {profileMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-[#161F30] rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                  <div className="px-2 py-1.5 border-b border-slate-100 dark:border-slate-800">
                    <p className="text-xs font-bold text-slate-900 dark:text-slate-100">
                      {user?.full_name || "Administrator"}
                    </p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                      {user?.email || "admin@company.internal"}
                    </p>
                    <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 text-[10px] font-semibold">
                      Role: {user?.role || "Owner"}
                    </span>
                  </div>

                  <div className="py-1">
                    <button
                      onClick={() => {
                        setProfileMenuOpen(false);
                        onNavigate("user_profile");
                      }}
                      className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 text-left transition"
                    >
                      <User className="w-3.5 h-3.5 text-slate-500" />
                      <span>Profile & Preferences</span>
                    </button>
                    <button
                      onClick={() => {
                        setProfileMenuOpen(false);
                        onNavigate("config_browser");
                      }}
                      className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 text-left transition"
                    >
                      <Sliders className="w-3.5 h-3.5 text-slate-500" />
                      <span>Browser Settings</span>
                    </button>
                  </div>

                  <div className="pt-1 border-t border-slate-100 dark:border-slate-800">
                    <button
                      onClick={() => {
                        setProfileMenuOpen(false);
                        onLogout();
                      }}
                      className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-left transition"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* VIEWPORT BODY */}
        <main className="flex-1 overflow-y-auto bg-[#F8FAFC] dark:bg-[#0B0F17]">
          {children}
        </main>
      </div>

      {/* 3. GLOBAL SEARCH MODAL (Ctrl + K) */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white dark:bg-[#161F30] rounded-2xl max-w-xl w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
            <div className="flex items-center px-4 py-3 border-b border-slate-200 dark:border-slate-800 gap-2">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search all 27 pages, flows, tests, DOM elements, or settings..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 bg-transparent border-none text-xs text-slate-900 dark:text-slate-100 focus:outline-none placeholder:text-slate-400"
              />
              <button
                onClick={() => setSearchOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto p-2 scrollbar-thin">
              {filteredSearchItems.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-400">
                  No matching platform pages or assets found.
                </div>
              ) : (
                <div className="space-y-1">
                  {filteredSearchItems.map((item) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          onNavigate(item.id);
                          setSearchOpen(false);
                          setSearchQuery("");
                        }}
                        className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-left transition"
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon className="w-4 h-4 text-[#2563EB] dark:text-blue-400" />
                          <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                            {item.label}
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                          {item.section}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40 flex items-center justify-between text-[11px] text-slate-400">
              <span>Select item to jump directly to page</span>
              <kbd className="px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono text-[10px]">
                ESC to close
              </kbd>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
