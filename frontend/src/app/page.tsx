"use client";

import React, { useEffect, useState } from "react";
import { AppShell, NavView } from "@/components/layout/AppShell";
import { EnterpriseLoginForm } from "@/components/auth/EnterpriseLoginForm";
import { BrowserAutomationLogo } from "@/components/common/BrowserLogo";

// Page Imports for all 27 Pages
import { DashboardOverview } from "@/components/dashboard/DashboardOverview"; // Page 1
import { AllFlowsPage } from "@/components/flows/AllFlowsPage"; // Page 2
import { VisualFlowBuilder } from "@/components/flows/VisualFlowBuilder"; // Page 3
import { CreateFlowPage } from "@/components/flows/CreateFlowPage"; // Page 4
import { SchedulesPage } from "@/components/flows/SchedulesPage"; // Page 5

import { TestCasesPage } from "@/components/testing/TestCasesPage"; // Page 6
import { TestSuitesPage } from "@/components/testing/TestSuitesPage"; // Page 7
import { VisualTestBuilder } from "@/components/testing/VisualTestBuilder"; // Page 8
import { TestReportsPage } from "@/components/testing/TestReportsPage"; // Page 9

import { LiveBrowserPage } from "@/components/browser/LiveBrowserPage"; // Page 10
import { DOMExplorerPage } from "@/components/browser/DOMExplorerPage"; // Page 11
import { ElementProfilesPage } from "@/components/browser/ElementProfilesPage"; // Page 12
import { ElementRecognitionPage } from "@/components/browser/ElementRecognitionPage"; // Page 13
import { SelfHealingPage } from "@/components/browser/SelfHealingPage"; // Page 14

import { RunningExecutionsPage } from "@/components/executions/RunningExecutionsPage"; // Page 15
import { ExecutionHistoryPage } from "@/components/executions/ExecutionHistoryPage"; // Page 16
import { ExecutionDetailsPage } from "@/components/executions/ExecutionDetailsPage"; // Page 17
import { ExecutionLogsPage } from "@/components/executions/ExecutionLogsPage"; // Page 18
import { ScreenshotsGalleryPage } from "@/components/executions/ScreenshotsGalleryPage"; // Page 19

import { ProjectsPage } from "@/components/config/ProjectsPage"; // Page 20
import { EnvironmentsPage } from "@/components/config/EnvironmentsPage"; // Page 21
import { CredentialsPage } from "@/components/config/CredentialsPage"; // Page 22
import { BrowserSettingsPage } from "@/components/config/BrowserSettingsPage"; // Page 23

import { UsersManagementPage } from "@/components/admin/UsersManagementPage"; // Page 24
import { RolesPermissionsPage } from "@/components/admin/RolesPermissionsPage"; // Page 25
import { AuditLogsPage } from "@/components/admin/AuditLogsPage"; // Page 26
import { UserProfilePage } from "@/components/admin/UserProfilePage"; // Page 27
import { projectsApi } from "@/api";

interface UserProfile {
  email: string;
  full_name?: string;
  role?: string;
}

export default function Home() {
  const [currentView, setCurrentView] = useState<NavView>("dashboard_overview");
  const [user, setUser] = useState<UserProfile | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string>("");
  const [selectedFlowId, setSelectedFlowId] = useState<string | undefined>(undefined);
  const [selectedTestId, setSelectedTestId] = useState<string | undefined>(undefined);

  const [currentProject, setCurrentProject] = useState<{ id: string; name: string }>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("active_project");
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed && parsed.id && parsed.id !== "p1-default") {
            return parsed;
          }
        }
      } catch {}
    }
    return {
      id: "",
      name: "",
    };
  });

  const handleSelectProject = (proj: { id: string; name: string }) => {
    setCurrentProject(proj);
    try {
      if (proj && proj.id) {
        localStorage.setItem("active_project", JSON.stringify(proj));
      } else {
        localStorage.removeItem("active_project");
      }
    } catch {}
  };

  // Sync real project UUID from backend API
  useEffect(() => {
    if (!user) return;
    projectsApi
      .list()
      .then((projects) => {
        if (projects && projects.length > 0) {
          try {
            const saved = localStorage.getItem("active_project");
            if (saved) {
              const parsed = JSON.parse(saved);
              const matching = projects.find((p: any) => p.id === parsed.id);
              if (matching) {
                handleSelectProject({ id: matching.id, name: matching.name });
                return;
              }
            }
          } catch {}
          // Select default project from backend with its valid UUID
          const first = projects[0];
          handleSelectProject({ id: first.id, name: first.name });
        } else {
          // No projects exist for this user - do not auto-create
          handleSelectProject({ id: "", name: "" });
        }
      })
      .catch((err) => {
        console.warn("Could not fetch projects list:", err);
      });
  }, [user]);

  // Check stored auth session on mount safely
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    const storedUser = localStorage.getItem("auth_user");
    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        setUser(null);
      }
    }

    const handleUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
    };
  }, []);

  function handleLogout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setUser(null);
  }

  // Auth View if unauthenticated
  if (!user) {
    return (
      <EnterpriseLoginForm
        standalone={true}
        onSuccessCallback={() => {
          try {
            const storedUser = localStorage.getItem("auth_user");
            if (storedUser) {
              setUser(JSON.parse(storedUser));
            }
          } catch {
            // Ignore parse errors
          }
        }}
      />
    );
  }

  // ---------------------------------------------------------------------------
  // Dedicated View Switcher for all 27 Pages
  // ---------------------------------------------------------------------------
  function renderView() {
    switch (currentView) {
      // 1. DASHBOARD
      case "dashboard_overview":
        return (
          <DashboardOverview
            onNavigate={setCurrentView}
            onSelectExecution={(id) => {
              setSelectedExecutionId(id);
              setCurrentView("executions_details");
            }}
          />
        );

      // 2. AUTOMATION
      case "automation_all_flows":
        return (
          <AllFlowsPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
            onSelectFlow={setSelectedFlowId}
          />
        );

      case "automation_builder":
        return (
          <VisualFlowBuilder
            projectId={currentProject.id}
            flowId={selectedFlowId}
            onNavigateHistory={() => setCurrentView("executions_history")}
          />
        );

      case "automation_create_flow":
        return (
          <CreateFlowPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
            onFlowCreated={(newId) => {
              setSelectedFlowId(newId);
              setCurrentView("automation_builder");
            }}
          />
        );

      case "automation_schedules":
        return (
          <SchedulesPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      // 3. TESTING
      case "testing_cases":
        return (
          <TestCasesPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
            onSelectTest={(id) => {
              setSelectedTestId(id);
              setCurrentView("testing_builder");
            }}
          />
        );

      case "testing_suites":
        return (
          <TestSuitesPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "testing_builder":
        return (
          <VisualTestBuilder
            projectId={currentProject.id}
            testCaseId={selectedTestId}
          />
        );

      case "testing_reports":
        return (
          <TestReportsPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
            onSelectExecution={(id) => {
              setSelectedExecutionId(id);
              setCurrentView("executions_details");
            }}
          />
        );

      // 4. BROWSER INTELLIGENCE
      case "browser_live":
        return (
          <LiveBrowserPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "browser_dom":
        return (
          <DOMExplorerPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "browser_profiles":
        return (
          <ElementProfilesPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "browser_recognition":
        return (
          <ElementRecognitionPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "browser_healing":
        return (
          <SelfHealingPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      // 5. EXECUTIONS
      case "executions_running":
        return (
          <RunningExecutionsPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
            onSelectExecution={(id) => {
              setSelectedExecutionId(id);
              setCurrentView("executions_details");
            }}
          />
        );

      case "executions_history":
        return (
          <ExecutionHistoryPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
            onSelectExecution={(id) => {
              setSelectedExecutionId(id);
              setCurrentView("executions_details");
            }}
          />
        );

      case "executions_details":
        return (
          <ExecutionDetailsPage
            executionId={selectedExecutionId}
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "executions_logs":
        return (
          <ExecutionLogsPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "executions_screenshots":
        return (
          <ScreenshotsGalleryPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      // 6. CONFIGURATION
      case "config_projects":
        return (
          <ProjectsPage
            currentProject={currentProject}
            onSelectProject={handleSelectProject}
            onNavigate={setCurrentView}
          />
        );

      case "config_environments":
        return (
          <EnvironmentsPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "config_credentials":
        return (
          <CredentialsPage
            projectId={currentProject.id}
            onNavigate={setCurrentView}
          />
        );

      case "config_browser":
        return <BrowserSettingsPage onNavigate={setCurrentView} />;

      // 7. ADMINISTRATION & SETTINGS
      case "admin_users":
        return <UsersManagementPage onNavigate={setCurrentView} />;

      case "admin_roles":
        return <RolesPermissionsPage onNavigate={setCurrentView} />;

      case "admin_audit":
        return <AuditLogsPage onNavigate={setCurrentView} />;

      case "user_profile":
        return (
          <UserProfilePage
            user={user}
            onLogout={handleLogout}
            onNavigate={setCurrentView}
          />
        );

      default:
        return (
          <DashboardOverview
            onNavigate={setCurrentView}
            onSelectExecution={(id) => {
              setSelectedExecutionId(id);
              setCurrentView("executions_details");
            }}
          />
        );
    }
  }

  return (
    <AppShell
      currentView={currentView}
      onNavigate={setCurrentView}
      user={user}
      onLogout={handleLogout}
      currentProject={currentProject}
    >
      {renderView()}
    </AppShell>
  );
}
