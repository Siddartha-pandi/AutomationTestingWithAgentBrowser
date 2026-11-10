"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { NavView } from "@/components/layout/AppShell";
import { projectsApi } from "@/api";

export interface ProjectInfo {
  id: string;
  name: string;
  description?: string;
}

interface AppContextType {
  currentView: NavView;
  setCurrentView: (view: NavView) => void;
  currentProject: ProjectInfo;
  setCurrentProject: (p: ProjectInfo) => void;
  projects: ProjectInfo[];
  refreshProjects: () => Promise<void>;
  selectedExecutionId: string;
  setSelectedExecutionId: (id: string) => void;
  selectedFlowId?: string;
  setSelectedFlowId: (id?: string) => void;
  selectedTestId?: string;
  setSelectedTestId: (id?: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppContextProvider({ children }: { children: React.ReactNode }) {
  const [currentView, setCurrentView] = useState<NavView>("dashboard_overview");
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [currentProject, setCurrentProjectState] = useState<ProjectInfo>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("active_project");
        if (saved) return JSON.parse(saved);
      } catch {
        // ignore
      }
    }
    return {
      id: "p1-default",
      name: "Enterprise QA Suite",
    };
  });

  const [selectedExecutionId, setSelectedExecutionId] = useState<string>("exec-run-101");
  const [selectedFlowId, setSelectedFlowId] = useState<string | undefined>(undefined);
  const [selectedTestId, setSelectedTestId] = useState<string | undefined>(undefined);

  const setCurrentProject = useCallback((p: ProjectInfo) => {
    setCurrentProjectState(p);
    try {
      localStorage.setItem("active_project", JSON.stringify(p));
    } catch {
      // ignore
    }
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      const list = await projectsApi.list();
      if (list && list.length > 0) {
        const mapped: ProjectInfo[] = list.map((item: any) => ({
          id: String(item.id),
          name: item.name,
          description: item.description,
        }));
        setProjects(mapped);

        // Check if current active project exists in the returned list
        const savedId = typeof window !== "undefined" ? localStorage.getItem("active_project_id") : null;
        const matching = mapped.find((p) => p.id === savedId) || mapped[mapped.length - 1]; // pick newest created project if newly registered
        if (matching) {
          setCurrentProject(matching);
        }
      }
    } catch {
      // API call failed / offline mode
    }
  }, [setCurrentProject]);

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  return (
    <AppContext.Provider
      value={{
        currentView,
        setCurrentView,
        currentProject,
        setCurrentProject,
        projects,
        refreshProjects,
        selectedExecutionId,
        setSelectedExecutionId,
        selectedFlowId,
        setSelectedFlowId,
        selectedTestId,
        setSelectedTestId,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppContextProvider");
  }
  return context;
}
