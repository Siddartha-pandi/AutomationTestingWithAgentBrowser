"use client";

import React, { useEffect } from "react";
import { useApp } from "@/context/AppContext";
import { AuthenticatedWorkspace } from "@/components/workspace/AuthenticatedWorkspace";

export default function AuthenticatedFlowsPage() {
  const { setCurrentView } = useApp();

  useEffect(() => {
    setCurrentView("automation_all_flows");
  }, [setCurrentView]);

  return <AuthenticatedWorkspace />;
}
