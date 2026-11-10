"use client";

import React from "react";
import { useApp } from "@/context/AppContext";
import { useAuth } from "@/context/AuthContext";
import { DashboardOverview } from "@/components/dashboard/DashboardOverview";
import { AllFlowsPage } from "@/components/flows/AllFlowsPage";
import { VisualFlowBuilder } from "@/components/flows/VisualFlowBuilder";
import { CreateFlowPage } from "@/components/flows/CreateFlowPage";
import { SchedulesPage } from "@/components/flows/SchedulesPage";
import { TestCasesPage } from "@/components/testing/TestCasesPage";
import { TestSuitesPage } from "@/components/testing/TestSuitesPage";
import { VisualTestBuilder } from "@/components/testing/VisualTestBuilder";
import { TestReportsPage } from "@/components/testing/TestReportsPage";
import { LiveBrowserPage } from "@/components/browser/LiveBrowserPage";
import { DOMExplorerPage } from "@/components/browser/DOMExplorerPage";
import { ElementProfilesPage } from "@/components/browser/ElementProfilesPage";
import { ElementRecognitionPage } from "@/components/browser/ElementRecognitionPage";
import { SelfHealingPage } from "@/components/browser/SelfHealingPage";
import { RunningExecutionsPage } from "@/components/executions/RunningExecutionsPage";
import { ExecutionHistoryPage } from "@/components/executions/ExecutionHistoryPage";
import { ExecutionDetailsPage } from "@/components/executions/ExecutionDetailsPage";
import { ExecutionLogsPage } from "@/components/executions/ExecutionLogsPage";
import { ScreenshotsGalleryPage } from "@/components/executions/ScreenshotsGalleryPage";
import { ProjectsPage } from "@/components/config/ProjectsPage";
import { EnvironmentsPage } from "@/components/config/EnvironmentsPage";
import { CredentialsPage } from "@/components/config/CredentialsPage";
import { BrowserSettingsPage } from "@/components/config/BrowserSettingsPage";
import { UsersManagementPage } from "@/components/admin/UsersManagementPage";
import { RolesPermissionsPage } from "@/components/admin/RolesPermissionsPage";
import { AuditLogsPage } from "@/components/admin/AuditLogsPage";
import { UserProfilePage } from "@/components/admin/UserProfilePage";

export function AuthenticatedWorkspace() {
  const { user, logout } = useAuth();
  const {
    currentView,
    setCurrentView,
    currentProject,
    setCurrentProject,
    selectedExecutionId,
    setSelectedExecutionId,
    selectedFlowId,
    setSelectedFlowId,
    selectedTestId,
    setSelectedTestId,
  } = useApp();

  switch (currentView) {
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

    case "config_projects":
      return (
        <ProjectsPage
          currentProject={currentProject}
          onSelectProject={setCurrentProject}
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
          onLogout={logout}
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

